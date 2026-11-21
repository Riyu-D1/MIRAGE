"""Sleeper Watch routes — /api/sleeper.

/simulate is live (core/sleeper_watch.check_drift). /register captures a
day-1 baseline in-process; durable persistence into sleeper_monitors is
TODO(T5/T6).
"""
import httpx
from fastapi import APIRouter, HTTPException

from ..core import sleeper_watch
from ..schemas import (
    SleeperCheckResult,
    SleeperRegisterRequest,
    SleeperSimulateRequest,
)

router = APIRouter(prefix="/sleeper", tags=["sleeper"])

# In-process baselines — replaced by sleeper_monitors table in T5/T6.
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
    # TODO(T5/T6): persist into sleeper_monitors + hand schedule to the
    # Grok Bot Routine (grokbot/ROUTINE.template.md).
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
    try:
        return sleeper_watch.check_drift(
            req.target_url,
            req.day,
            baseline_hash=baseline[0] if baseline else None,
            baseline_gateway=baseline[1] if baseline else None,
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"sleeper fetch failed: {e}")
