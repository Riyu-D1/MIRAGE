"""Sleeper Watch — Day 1 -> Day 60 post-onboarding drift monitor (T5)."""
from ..schemas import SleeperCheckResult


def check_drift(
    target_url: str,
    day: int,
    baseline_hash: str | None = None,
    baseline_gateway: str | None = None,
) -> SleeperCheckResult:
    """Compare a merchant's day-N surface to its day-1 approved baseline.

    TODO(T5): fetch target-merchant /sleeper?day=N (or load stored captures),
    SHA-256 the HTML, extract the gateway, then compare to baseline:
      * intact = hashes match AND gateway unchanged
      * alert_triggered = not intact
      * include both hashes + both gateways in the result
    Persistence of baselines into sleeper_monitors is part of this ticket.
    """
    raise NotImplementedError("T5 — implement per docs/TASKS.md")
