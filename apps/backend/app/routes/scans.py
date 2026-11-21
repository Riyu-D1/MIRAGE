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
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..config import settings
from ..core import diff_engine, injection_scanner, replay_engine
from ..core.playwright_probe import DESKTOP_UA, capture_both_personas
from ..integrations import osint_client
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
    scan_id: str, step: str, status: str, detail: str, latency_ms: float | None = None
) -> AgentEvent:
    return AgentEvent(
        id=str(uuid.uuid4()),
        scan_id=scan_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        step=step,
        agent="mirage-backend",
        status=status,  # type: ignore[arg-type]
        detail=detail,
        latency_ms=latency_ms,
    )


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
    events = _EVENT_STORE[scan.scan_id]
    scan_dir = _scan_dir(scan.scan_id)
    scan_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: dual-persona probe ─────────────────────────────────────────
    events.append(_event(scan.scan_id, "probe.capture", "running", "Launching dual-persona probe"))
    t0 = time.perf_counter()
    try:
        a, b = asyncio.run(
            capture_both_personas(scan.target_url, scan.scan_id, scan_dir)
        )
        scan.persona_a, scan.persona_b = a, b
        events.append(
            _event(
                scan.scan_id,
                "probe.capture",
                "done",
                f"A+B captured @1280x800 · {len(a.detected_items)}v{len(b.detected_items)} items",
                (time.perf_counter() - t0) * 1000,
            )
        )
        html_a = (scan_dir / "persona_a.html").read_text(errors="replace")
        boxes = _load_boxes(scan_dir)
    except Exception as e:  # probe failure must never 500 the scan
        events.append(
            _event(scan.scan_id, "probe.capture", "error", f"probe failed: {e}",
                   (time.perf_counter() - t0) * 1000)
        )
        html_a = _fetch_page(scan.target_url)
        boxes = {}
        if html_a is None:
            return

    # ── Step 2: injection scan on Persona A's page ─────────────────────────
    t0 = time.perf_counter()
    scan.injections = injection_scanner.scan_html(html_a, boxes)
    events.append(
        _event(
            scan.scan_id,
            "injection.scan",
            "alert" if scan.injections else "done",
            f"{len(scan.injections)} hidden payloads across "
            f"{len({f.channel for f in scan.injections})} channels",
            (time.perf_counter() - t0) * 1000,
        )
    )

    # ── Step 3: divergence diff + reality gap ──────────────────────────────
    if scan.persona_a and scan.persona_b:
        scan.divergence = diff_engine.compute_divergence(
            scan.persona_a, scan.persona_b, scan.scan_id, scan_dir
        )
        scan.reality_gap_score = diff_engine.reality_gap_score(scan.divergence)
        d = scan.divergence
        events.append(
            _event(
                scan.scan_id,
                "diff.compute",
                "alert" if (d.checkout_swapped or d.descriptor_swapped) else "done",
                f"gap {scan.reality_gap_score}/100 · checkout_swapped={d.checkout_swapped} · "
                f"pixels {d.pixel_divergence_pct}% · jaccard {d.text_jaccard_distance}",
                d.compute_ms,
            )
        )

    # ── Step 4: OSINT enrich (live keys -> live, else cached fixtures) ──────
    t0 = time.perf_counter()
    merchant = urlparse(scan.target_url).hostname or scan.target_url
    try:
        scan.osint = osint_client.enrich(merchant)
        events.append(
            _event(
                scan.scan_id,
                "osint.enrich",
                "done",
                f"{scan.osint.source_mode} · {len(scan.osint.adverse_media_hits)} media hits",
                (time.perf_counter() - t0) * 1000,
            )
        )
    except Exception as e:
        events.append(_event(scan.scan_id, "osint.enrich", "error", str(e),
                             (time.perf_counter() - t0) * 1000))

    # ── Step 5: verdict (precedence: cloaked > injection > drift > clean) ──
    d = scan.divergence
    if d and (d.checkout_swapped or scan.reality_gap_score >= 70):
        scan.verdict = Verdict.CLOAKED_CRITICAL
    elif scan.injections:
        scan.verdict = Verdict.INJECTION_DETECTED
    else:
        scan.verdict = Verdict.VERIFIED_CLEAN
    events.append(
        _event(
            scan.scan_id,
            "verdict",
            "alert" if scan.verdict != Verdict.VERIFIED_CLEAN else "done",
            scan.verdict.value,
        )
    )

    # ── Step 6: evidence manifest + merkle hash ────────────────────────────
    (scan_dir / "scan.json").write_text(scan.model_dump_json(indent=2))
    manifest = replay_engine.build_manifest(scan_dir)
    scan.evidence_merkle_hash = diff_engine.merkle_hash(list(manifest.values()))


@router.post("/scans", response_model=ScanResult)
def create_scan(req: ScanRequest) -> ScanResult:
    """Create a scan and run the deterministic pipeline."""
    scan = ScanResult(
        scan_id=str(uuid.uuid4()),
        target_url=req.url,
        created_at=datetime.now(timezone.utc).isoformat(),
        verdict=Verdict.PENDING,
        reality_gap_score=0,
        evidence_merkle_hash="",
    )
    _SCAN_STORE[scan.scan_id] = scan
    _EVENT_STORE[scan.scan_id] = [
        _event(scan.scan_id, "scan.created", "done", f"Scan queued for {req.url}"),
    ]
    _run_pipeline(scan)
    _SCAN_STORE[scan.scan_id] = scan
    return scan


@router.get("/scans/{scan_id}", response_model=ScanResult)
def get_scan(scan_id: str) -> ScanResult:
    scan = _SCAN_STORE.get(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return scan


@router.get("/scans/{scan_id}/stream")
async def stream_scan(scan_id: str) -> StreamingResponse:
    """SSE stream of AgentEvents for a scan.

    TODO(T6): back with the live async event bus; replay persisted events for
    late subscribers, then tail until terminal status.
    """
    if scan_id not in _SCAN_STORE:
        raise HTTPException(status_code=404, detail="scan not found")

    async def gen() -> AsyncIterator[str]:
        for ev in _EVENT_STORE.get(scan_id, []):
            yield f"data: {json.dumps(ev.model_dump(mode='json'))}\n\n"
        yield 'data: {"terminal": true}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/scans/{scan_id}/replay", response_model=ReplayVerification)
def replay_scan(scan_id: str) -> ReplayVerification:
    """Zero-LLM deterministic re-verification of stored artifacts."""
    if scan_id not in _SCAN_STORE:
        raise HTTPException(status_code=404, detail="scan not found")
    return replay_engine.replay(scan_id, settings.artifacts_path)


@router.get("/scans/{scan_id}/dossier")
def get_dossier(scan_id: str, format: str = "json") -> dict:
    """Printable evidence dossier (JSON now; HTML rendering in T5)."""
    scan = _SCAN_STORE.get(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    # TODO(T5): format=html -> standalone printable HTML dossier with all
    # artifact hashes, captures, findings, verdict, and replay result.
    return {
        "scan_id": scan.scan_id,
        "format": format,
        "dossier": scan.model_dump(mode="json"),
        "events": [e.model_dump(mode="json") for e in _EVENT_STORE.get(scan_id, [])],
        "replay": replay_engine.replay(scan_id, settings.artifacts_path).model_dump(mode="json"),
    }
