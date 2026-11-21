"""Sleeper Watch — Day 1 -> Day 60 post-onboarding drift monitor (T5 — core
check implemented; persistence into sleeper_monitors still TODO(T5))."""
import hashlib
import re

import httpx

from ..schemas import SleeperCheckResult

_GW_RE = re.compile(r'x-checkout-endpoint"\s+content="([^"]+)"')
_DESC_RE = re.compile(r'x-billing-descriptor"\s+content="([^"]+)"')


def _fetch_surface(target_url: str, day: int) -> str:
    url = f"{target_url.rstrip('/')}/sleeper?day={day}"
    resp = httpx.get(url, timeout=10.0)
    resp.raise_for_status()
    return resp.text


def _hash(html: str) -> str:
    return hashlib.sha256(html.encode()).hexdigest()


def _gateway(html: str) -> str:
    m = _GW_RE.search(html)
    return m.group(1) if m else ""


def check_drift(
    target_url: str,
    day: int,
    baseline_hash: str | None = None,
    baseline_gateway: str | None = None,
) -> SleeperCheckResult:
    """Compare a merchant's day-N surface to its day-1 approved baseline.

    When baseline values are omitted, day-1 is fetched live and used as the
    baseline (self-baselining for the demo). TODO(T5): read baselines from the
    sleeper_monitors table instead; capture screenshot via playwright_probe.
    """
    if baseline_hash is None or baseline_gateway is None:
        baseline = _fetch_surface(target_url, 1)
        baseline_hash = baseline_hash or _hash(baseline)
        baseline_gateway = baseline_gateway if baseline_gateway is not None else _gateway(baseline)

    current = _fetch_surface(target_url, day)
    current_hash = _hash(current)
    current_gateway = _gateway(current)

    intact = current_hash == baseline_hash and current_gateway == baseline_gateway
    return SleeperCheckResult(
        target_url=target_url,
        day=day,
        intact=intact,
        baseline_hash=baseline_hash,
        current_hash=current_hash,
        baseline_gateway=baseline_gateway or "",
        current_gateway=current_gateway,
        alert_triggered=not intact,
        screenshot_url=None,  # TODO(T5): probe-captured evidence screenshot
    )
