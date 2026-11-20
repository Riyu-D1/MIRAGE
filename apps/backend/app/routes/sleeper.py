"""Sleeper Watch routes — /api/sleeper.

Stub implementation. # TODO(T5): wire core/sleeper_watch for real hash-drift
checks; Grok Bot Routine triggers these via the MCP server (T7).
"""
from fastapi import APIRouter

from ..schemas import (
    SleeperCheckResult,
    SleeperRegisterRequest,
    SleeperSimulateRequest,
)

router = APIRouter(prefix="/sleeper", tags=["sleeper"])


@router.post("/register")
def register_sleeper(req: SleeperRegisterRequest) -> dict:
    """Register a freshly-approved merchant for Day 1->60 drift monitoring.

    TODO(T5): capture baseline DOM/checkout hashes into sleeper_monitors and
    hand the schedule to the Grok Bot Routine (see grokbot/ROUTINE.template.md).
    """
    return {
        "registered": True,
        "target_url": req.target_url,
        "note": "stub — baseline capture + persistence implemented in T5",
    }


@router.post("/simulate", response_model=SleeperCheckResult)
def simulate_sleeper(req: SleeperSimulateRequest) -> SleeperCheckResult:
    """Simulate a sleeper-watch check at a given day.

    TODO(T5): call core/sleeper_watch.check_drift() against
    target-merchant /sleeper?day=N (or stored captures).
    """
    return SleeperCheckResult(
        target_url=req.target_url,
        day=req.day,
        intact=True,
        baseline_hash="0" * 64,
        current_hash="0" * 64,
        baseline_gateway="",
        current_gateway="",
        alert_triggered=False,
        screenshot_url=None,
    )
