"""Scan routes — /api/scans.

Minimal sync pipeline is live so the demo path works end-to-end:
POST /scans fetches the target HTML as Persona A, runs the deterministic
injection scanner, and sets the verdict. TODO(T6): replace _run_pipeline_sync
with the full async pipeline (playwright_probe -> diff_engine -> OSINT ->
persistence via supabase_client + live SSE event bus).
"""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..core import injection_scanner
from ..core.playwright_probe import DESKTOP_UA
from ..schemas import (
    AgentEvent,
    ReplayCheck,
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


def _run_pipeline_sync(scan: ScanResult) -> None:
    """Synchronous starter pipeline (replaced by T6's async probe pipeline).

    Runs the deterministic injection scan only — persona captures, divergence,
    heatmap, and OSINT enrichment land in T2/T3/T6.
    """
    events = _EVENT_STORE[scan.scan_id]
    events.append(_event(scan.scan_id, "scan.fetch", "running", f"Fetching {scan.target_url}"))
    t0 = time.perf_counter()
    html = _fetch_page(scan.target_url)
    fetch_ms = (time.perf_counter() - t0) * 1000

    if html is None:
        events.append(
            _event(scan.scan_id, "scan.fetch", "error", "target unreachable", fetch_ms)
        )
        return
    events.append(
        _event(scan.scan_id, "scan.fetch", "done", f"{len(html)} bytes captured", fetch_ms)
    )

    t0 = time.perf_counter()
    findings = injection_scanner.scan_html(html)
    scan_ms = (time.perf_counter() - t0) * 1000
    scan.injections = findings
    status = "alert" if findings else "done"
    events.append(
        _event(
            scan.scan_id,
            "injection.scan",
            status,
            f"{len(findings)} hidden payloads across "
            f"{len({f.channel for f in findings})} channels",
            scan_ms,
        )
    )

    if findings:
        scan.verdict = Verdict.INJECTION_DETECTED
    # TODO(T6): verdict precedence once divergence lands —
    # CLOAKED_CRITICAL > INJECTION_DETECTED > DRIFT_DETECTED > VERIFIED_CLEAN.


@router.post("/scans", response_model=ScanResult)
def create_scan(req: ScanRequest) -> ScanResult:
    """Create a scan and run the starter pipeline synchronously."""
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
    _run_pipeline_sync(scan)
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
    """Zero-LLM deterministic re-verification of stored artifacts.

    TODO(T5): delegate to core/replay_engine.replay(scan_id, artifacts_dir).
    """
    if scan_id not in _SCAN_STORE:
        raise HTTPException(status_code=404, detail="scan not found")
    return ReplayVerification(
        scan_id=scan_id,
        verified=False,
        llm_calls=0,
        elapsed_ms=0.0,
        hash_integrity="MISMATCH",
        checks=[
            ReplayCheck(
                name="stub",
                passed=False,
                detail="replay engine not implemented yet — see docs/TASKS.md T5",
            )
        ],
    )


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
        "note": "stub dossier — full evidence dossier implemented in T5",
    }
