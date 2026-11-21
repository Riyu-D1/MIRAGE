"""Scan routes — /api/scans.

The deterministic pipeline is live:
  playwright probe (dual persona, 1280x800) -> injection scan -> divergence
  diff + reality gap -> OSINT enrich -> verdict -> artifact manifest.
TODO(T6): swap in-process stores for supabase_client/SQLite, run the pipeline
as a background task (async SSE bus instead of post-hoc event replay), and
dispatch events to integrations/grokbot_client.
"""
import asyncio
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..config import settings
from ..core import diff_engine, injection_scanner, replay_engine
from ..core.playwright_probe import DESKTOP_UA, capture_both_personas
from ..integrations import grokbot_client, osint_client
from ..integrations.supabase_client import store
from ..schemas import (
    AgentEvent,
    BoundingBox,
    ReplayVerification,
    ScanRequest,
    ScanResult,
    Verdict,
)

router = APIRouter(tags=["scans"])

# In-process store — replaced by supabase_client/SQLite in T6.
_SCAN_STORE: dict[str, ScanResult] = {}
_EVENT_STORE: dict[str, list[AgentEvent]] = {}


def _event(
    scan_id: str,
    step: str,
    status: str,
    detail: str,
    latency_ms: float | None = None,
    agent: str = "mirage-backend",
) -> AgentEvent:
    """Emit an AgentEvent: persist it and dispatch to the Grok Bot webhook
    (skipped for grok-bot-originated events to avoid a webhook echo loop)."""
    ev = AgentEvent(
        id=str(uuid.uuid4()),
        scan_id=scan_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        step=step,
        agent=agent,
        status=status,  # type: ignore[arg-type]
        detail=detail,
        latency_ms=latency_ms,
    )
    _EVENT_STORE.setdefault(scan_id, []).append(ev)
    store.insert_event(ev)
    if agent == "mirage-backend":
        grokbot_client.dispatch_event_sync(ev)
    return ev


def _fetch_page(url: str) -> str | None:
    """Fetch raw HTML as Persona A (direct desktop compliance reviewer)."""
    try:
        resp = httpx.get(url, headers={"User-Agent": DESKTOP_UA}, timeout=10.0)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError:
        return None


def _scan_dir(scan_id: str) -> Path:
    return settings.artifacts_path / scan_id


def _load_boxes(scan_dir: Path) -> dict[str, BoundingBox]:
    path = scan_dir / "persona_a_boxes.json"
    if not path.exists():
        return {}
    return {k: BoundingBox(**v) for k, v in json.loads(path.read_text()).items()}


def _run_pipeline(scan: ScanResult) -> None:
    """Full deterministic pipeline. Runs in the route's worker thread, so
    asyncio.run() can drive the async probe safely."""
    scan_dir = _scan_dir(scan.scan_id)
    scan_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: dual-persona probe ─────────────────────────────────────────
    _event(scan.scan_id, "probe.capture", "running", "Launching dual-persona probe")
    t0 = time.perf_counter()
    try:
        a, b = asyncio.run(
            capture_both_personas(scan.target_url, scan.scan_id, scan_dir)
        )
        scan.persona_a, scan.persona_b = a, b
        _event(
            scan.scan_id,
            "probe.capture",
            "done",
            f"A+B captured @1280x800 · {len(a.detected_items)}v{len(b.detected_items)} items",
            (time.perf_counter() - t0) * 1000,
        )
        html_a = (scan_dir / "persona_a.html").read_text(errors="replace")
        boxes = _load_boxes(scan_dir)
    except Exception as e:  # probe failure must never 500 the scan
        _event(scan.scan_id, "probe.capture", "error", f"probe failed: {e}",
               (time.perf_counter() - t0) * 1000)
        html_a = _fetch_page(scan.target_url)
        boxes = {}
        if html_a is None:
            _event(scan.scan_id, "pipeline.error", "error",
                   "target unreachable — scan aborted")
            return

    # ── Step 2: injection scan on Persona A's page ─────────────────────────
    t0 = time.perf_counter()
    scan.injections = injection_scanner.scan_html(html_a, boxes)
    _event(
        scan.scan_id,
        "injection.scan",
        "alert" if scan.injections else "done",
        f"{len(scan.injections)} hidden payloads across "
        f"{len({f.channel for f in scan.injections})} channels",
        (time.perf_counter() - t0) * 1000,
    )

    # ── Step 3: divergence diff + reality gap ──────────────────────────────
    if scan.persona_a and scan.persona_b:
        scan.divergence = diff_engine.compute_divergence(
            scan.persona_a, scan.persona_b, scan.scan_id, scan_dir
        )
        scan.reality_gap_score = diff_engine.reality_gap_score(scan.divergence)
        d = scan.divergence
        _event(
            scan.scan_id,
            "diff.compute",
            "alert" if (d.checkout_swapped or d.descriptor_swapped) else "done",
            f"gap {scan.reality_gap_score}/100 · checkout_swapped={d.checkout_swapped} · "
            f"pixels {d.pixel_divergence_pct}% · jaccard {d.text_jaccard_distance}",
            d.compute_ms,
        )

    # ── Step 4: OSINT enrich (live keys -> live, else cached fixtures) ──────
    t0 = time.perf_counter()
    merchant = urlparse(scan.target_url).hostname or scan.target_url
    try:
        scan.osint = osint_client.enrich(merchant)
        _event(
            scan.scan_id,
            "osint.enrich",
            "done",
            f"{scan.osint.source_mode} · {len(scan.osint.adverse_media_hits)} media hits",
            (time.perf_counter() - t0) * 1000,
        )
    except Exception as e:
        _event(scan.scan_id, "osint.enrich", "error", str(e),
               (time.perf_counter() - t0) * 1000)

    # ── Step 5: verdict (precedence: cloaked > injection > drift > clean) ──
    d = scan.divergence
    if d and (d.checkout_swapped or scan.reality_gap_score >= 70):
        scan.verdict = Verdict.CLOAKED_CRITICAL
    elif scan.injections:
        scan.verdict = Verdict.INJECTION_DETECTED
    else:
        scan.verdict = Verdict.VERIFIED_CLEAN
    _event(
        scan.scan_id,
        "verdict",
        "alert" if scan.verdict != Verdict.VERIFIED_CLEAN else "done",
        scan.verdict.value,
    )

    # ── Step 6: evidence manifest + merkle hash + persistence ──────────────
    (scan_dir / "scan.json").write_text(scan.model_dump_json(indent=2))
    manifest = replay_engine.build_manifest(scan_dir)
    scan.evidence_merkle_hash = diff_engine.merkle_hash(list(manifest.values()))
    for name, sha in manifest.items():
        store.record_artifact(
            scan.scan_id, "artifact", f"/artifacts/{scan.scan_id}/{name}", sha
        )
    store.upsert_scan(scan)
    _event(scan.scan_id, "pipeline.complete", "done",
           f"evidence sealed · merkle {scan.evidence_merkle_hash[:12]}…")


@router.post("/scans", response_model=ScanResult)
def create_scan(req: ScanRequest) -> ScanResult:
    """Create a scan and run the deterministic pipeline in a background
    thread — returns a PENDING ScanResult immediately so the client can
    open the SSE stream and watch events arrive live. Poll GET /scans/{id}
    (or refetch on the stream's terminal event) for the final result."""
    scan = ScanResult(
        scan_id=str(uuid.uuid4()),
        target_url=req.url,
        created_at=datetime.now(timezone.utc).isoformat(),
        verdict=Verdict.PENDING,
        reality_gap_score=0,
        evidence_merkle_hash="",
    )
    _SCAN_STORE[scan.scan_id] = scan
    store.upsert_scan(scan)
    _event(scan.scan_id, "scan.created", "done", f"Scan queued for {req.url}")
    threading.Thread(target=_run_pipeline, args=(scan,), daemon=True).start()
    return scan


@router.get("/scans", response_model=list[ScanResult])
def list_scans(limit: int = 50) -> list[ScanResult]:
    """Recent scans, newest first — in-process plus persisted."""
    seen: dict[str, ScanResult] = {s.scan_id: s for s in store.list_scans(limit)}
    seen.update(_SCAN_STORE)  # in-process wins (includes in-flight scans)
    return sorted(seen.values(), key=lambda s: s.created_at, reverse=True)[:limit]


@router.get("/scans/{scan_id}", response_model=ScanResult)
def get_scan(scan_id: str) -> ScanResult:
    scan = _SCAN_STORE.get(scan_id) or store.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return scan


_TERMINAL_STEPS = {"pipeline.complete", "pipeline.error"}


def _all_events(scan_id: str) -> list[AgentEvent]:
    """In-process + persisted events, deduped by id, ordered by timestamp.

    Both sources can be partial: in-process misses events emitted before a
    restart; persisted can lag an in-flight insert. Union covers both.
    """
    merged: dict[str, AgentEvent] = {
        e.id: e for e in store.list_events(scan_id)
    }
    merged.update({e.id: e for e in _EVENT_STORE.get(scan_id, [])})
    return sorted(merged.values(), key=lambda e: e.timestamp)


@router.get("/scans/{scan_id}/stream")
async def stream_scan(scan_id: str) -> StreamingResponse:
    """SSE stream of AgentEvents for a scan.

    The pipeline runs in a background thread, so this stream is live:
    stored events replay with a short pacing delay, then the tail poll
    picks up new events every ~200ms until pipeline.complete / error or a
    90s cap. Clients should refetch GET /scans/{id} on terminal.
    """
    if scan_id not in _SCAN_STORE and not _all_events(scan_id):
        raise HTTPException(status_code=404, detail="scan not found")

    async def gen() -> AsyncIterator[str]:
        sent: set[str] = set()
        deadline = time.monotonic() + 90.0
        while True:
            events = _all_events(scan_id)
            fresh = [e for e in events if e.id not in sent]
            terminal_seen = False
            for ev in fresh:
                sent.add(ev.id)
                yield f"data: {json.dumps(ev.model_dump(mode='json'))}\n\n"
                terminal_seen = terminal_seen or ev.step in _TERMINAL_STEPS
                await asyncio.sleep(0.25)  # pacing — replay reads like live
            if terminal_seen or time.monotonic() > deadline:
                break
            await asyncio.sleep(0.2)  # tail poll
        yield 'data: {"terminal": true}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/scans/{scan_id}/replay", response_model=ReplayVerification)
def replay_scan(scan_id: str) -> ReplayVerification:
    """Zero-LLM deterministic re-verification of stored artifacts."""
    if scan_id not in _SCAN_STORE and store.get_scan(scan_id) is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return replay_engine.replay(scan_id, settings.artifacts_path)


def _dossier_html(scan: ScanResult, replay: ReplayVerification, events: list[AgentEvent]) -> str:
    """Standalone printable evidence dossier — all hashes, captures,
    findings, verdict, and replay result. Self-contained (inline styles)."""
    import html as h

    def esc(s: object) -> str:
        return h.escape(str(s if s is not None else "—"))

    inj_rows = "".join(
        f"<tr><td>{esc(f.channel.value)}</td><td class='sev'>{f.severity}</td>"
        f"<td><code>{esc(f.raw_payload)[:140]}</code></td><td>{esc(f.dom_selector)}</td></tr>"
        for f in scan.injections
    )
    ev_rows = "".join(
        f"<tr><td><code>{esc(e.step)}</code></td><td>{esc(e.status)}</td>"
        f"<td>{esc(e.detail)}</td><td>{'-' if e.latency_ms is None else f'{e.latency_ms:.1f}ms'}</td></tr>"
        for e in events
    )
    chk_rows = "".join(
        f"<tr><td>{'PASS' if c.passed else 'FAIL'}</td><td>{esc(c.name)}</td><td>{esc(c.detail)}</td></tr>"
        for c in replay.checks
    )
    d = scan.divergence
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>MIRAGE Evidence Dossier — {esc(scan.scan_id)}</title>
<style>
  body{{font-family:ui-monospace,Menlo,monospace;background:#0d0f16;color:#edeff5;padding:32px;max-width:960px;margin:auto}}
  h1{{color:#37e0d8;font-size:22px}} h2{{color:#9aa3b8;font-size:13px;text-transform:uppercase;letter-spacing:.1em;margin-top:28px}}
  table{{border-collapse:collapse;width:100%;font-size:12px}} td,th{{border:1px solid #232a3d;padding:6px 8px;text-align:left;vertical-align:top}}
  code{{color:#37e0d8;word-break:break-all}} .sev{{color:#ff3b5c;font-weight:bold}} .verdict{{font-size:20px;font-weight:bold;color:#ff3b5c}}
  .ok{{color:#2fd67a}} .box{{border:1px solid #232a3d;padding:12px 16px;border-radius:8px;background:#141824}}
  @media print{{body{{background:#fff;color:#111}} code{{color:#064}} }}
</style></head><body>
<h1>MIRAGE EVIDENCE DOSSIER</h1>
<div class="box">
  <p>scan_id: <code>{esc(scan.scan_id)}</code></p>
  <p>target: <code>{esc(scan.target_url)}</code> · captured: {esc(scan.created_at)}</p>
  <p class="verdict">VERDICT: {esc(scan.verdict.value)} · reality-gap {scan.reality_gap_score}/100</p>
  <p>evidence merkle: <code>{esc(scan.evidence_merkle_hash)}</code></p>
</div>
<h2>Dual-Persona Captures</h2>
<table><tr><th>persona</th><th>gateway</th><th>descriptor</th><th>html sha256</th><th>items</th></tr>
{"".join(f"<tr><td>{esc(p.persona if p else '')}</td><td><code>{esc(p.checkout_endpoint if p else None)}</code></td><td>{esc(p.billing_descriptor if p else None)}</td><td><code>{esc((p.html_sha256 or '')[:20])}…</code></td><td>{esc(', '.join(p.detected_items) if p else '')}</td></tr>" for p in (scan.persona_a, scan.persona_b))}
</table>
<h2>Divergence</h2>
<table><tr><th>checkout_swapped</th><th>descriptor_swapped</th><th>pixel %</th><th>jaccard</th><th>compute_ms</th></tr>
<tr><td>{esc(d.checkout_swapped if d else None)}</td><td>{esc(d.descriptor_swapped if d else None)}</td><td>{esc(d.pixel_divergence_pct if d else None)}</td><td>{esc(d.text_jaccard_distance if d else None)}</td><td>{esc(d.compute_ms if d else None)}</td></tr></table>
<h2>Prompt-Injection Findings ({len(scan.injections)})</h2>
<table><tr><th>channel</th><th>severity</th><th>payload</th><th>selector</th></tr>{inj_rows}</table>
<h2>Mission Log</h2>
<table><tr><th>step</th><th>status</th><th>detail</th><th>latency</th></tr>{ev_rows}</table>
<h2>Regulator Replay — {replay.llm_calls} LLM calls · {replay.elapsed_ms:.1f}ms · <span class="ok">{esc(replay.hash_integrity)}</span></h2>
<table><tr><th>check</th><th>name</th><th>detail</th></tr>{chk_rows}</table>
<p style="color:#9aa3b8;font-size:11px;margin-top:24px">Generated deterministically by MIRAGE — 0 LLM calls in every forensic check.</p>
</body></html>"""


@router.get("/scans/{scan_id}/dossier")
def get_dossier(scan_id: str, format: str = "json") -> Any:
    """Evidence dossier — JSON or standalone printable HTML (?format=html)."""
    scan = _SCAN_STORE.get(scan_id) or store.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    replay = replay_engine.replay(scan_id, settings.artifacts_path)
    events = _EVENT_STORE.get(scan_id) or store.list_events(scan_id)
    if format == "html":
        from fastapi.responses import HTMLResponse

        return HTMLResponse(_dossier_html(scan, replay, events))
    return {
        "scan_id": scan.scan_id,
        "format": format,
        "dossier": scan.model_dump(mode="json"),
        "events": [e.model_dump(mode="json") for e in events],
        "replay": replay.model_dump(mode="json"),
    }
