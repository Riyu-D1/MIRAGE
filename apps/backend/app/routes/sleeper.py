"""Sleeper Watch routes — /api/sleeper.

/simulate is live (core/sleeper_watch.check_drift). /register persists a
day-1 baseline into sleeper_monitors (SQLite or Supabase) so monitors
survive restarts; an in-process cache avoids a DB hit when available.

TODO(T5): hand the schedule to a Grok Bot Routine (grokbot/ROUTINE.template.md)
— the routine calls /api/sleeper/simulate daily and reads GET /monitors.
"""
import httpx
from fastapi import APIRouter, HTTPException

from ..core import sleeper_watch
from ..integrations.supabase_client import store
from ..schemas import (
    SleeperCheckResult,
    SleeperRegisterRequest,
    SleeperSimulateRequest,
)

router = APIRouter(prefix="/sleeper", tags=["sleeper"])

# In-process cache of baselines — DB (sleeper_monitors) is the source of truth.
_BASELINES: dict[str, tuple[str, str]] = {}


@router.post("/register")
def register_sleeper(req: SleeperRegisterRequest) -> dict:
    """Capture a day-1 baseline hash + gateway for drift monitoring."""
    try:
        baseline = sleeper_watch._fetch_surface(req.target_url, 1)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"baseline fetch failed: {e}")
    baseline_hash = sleeper_watch._hash(baseline)
    baseline_gateway = sleeper_watch._gateway(baseline)
    _BASELINES[req.target_url] = (baseline_hash, baseline_gateway)
    store.register_monitor(req.target_url, baseline_hash, baseline_gateway)
    return {
        "registered": True,
        "target_url": req.target_url,
        "baseline_hash": baseline_hash,
        "baseline_gateway": baseline_gateway,
    }


@router.post("/simulate", response_model=SleeperCheckResult)
def simulate_sleeper(req: SleeperSimulateRequest) -> SleeperCheckResult:
    """Run a sleeper drift check at day N."""
    baseline = _BASELINES.get(req.target_url)
    if baseline is None:
        row = store.get_monitor(req.target_url)
        if row:
            baseline = (row["baseline_hash"], row.get("baseline_gateway"))
            _BASELINES[req.target_url] = baseline  # type: ignore[assignment]
    try:
        result = sleeper_watch.check_drift(
            req.target_url,
            req.day,
            baseline_hash=baseline[0] if baseline else None,
            baseline_gateway=baseline[1] if baseline else None,
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"sleeper fetch failed: {e}")
    store.update_monitor(req.target_url, result)
    return result


@router.get("/monitors")
def list_monitors() -> list[dict]:
    """All persisted sleeper monitors — baseline, last check, alert state."""
    # store.get_monitor is per-url; for listing, query the table directly.
    try:
        if store.enabled:
            return store._sb.table("sleeper_monitors").select("*").execute().data
        import sqlite3

        with store._sqlite() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT * FROM sleeper_monitors ORDER BY registered_at DESC"
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            import json

            d["history"] = json.loads(d.get("history") or "[]")
            out.append(d)
        return out
    except Exception:
        return []
