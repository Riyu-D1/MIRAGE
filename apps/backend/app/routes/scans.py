"""Scan routes — /api/scans.

Stub implementation: endpoints return valid typed responses immediately.
# TODO(T6): run the T2->T5 forensic pipeline as an async task, persist via
integrations/supabase_client (SQLite fallback), and stream real AgentEvents.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

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


def _event(scan_id: str, step: str, status: str, detail: str) -> AgentEvent:
    return AgentEvent(
        id=str(uuid.uuid4()),
        scan_id=scan_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        step=step,
        agent="mirage-backend",
        status=status,  # type: ignore[arg-type]
        detail=detail,
        latency_ms=None,
    )


@router.post("/scans", response_model=ScanResult)
def create_scan(req: ScanRequest) -> ScanResult:
    """Create a scan and kick off the forensic pipeline.

    TODO(T6): replace the canned PENDING result with an async task running
    playwright_probe -> diff_engine -> injection_scanner -> osint, emitting
    AgentEvents at each step.
    """
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
