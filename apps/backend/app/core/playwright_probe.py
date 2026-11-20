"""Dual-persona Playwright probe (T2).

Captures the same URL as Persona A (direct desktop compliance reviewer) and
Persona B (mobile UA + social Referer buyer). BOTH personas render at exactly
1280x800 — pixel alignment is required for the WipeSlider + heatmap
(AGENTS.md §4). Do NOT set is_mobile=True or device_scale_factor.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Literal

from playwright.async_api import Browser, async_playwright

from ..config import settings
from ..schemas import PersonaCapture

# Locked capture geometry — never change (AGENTS.md §4).
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 800

PersonaKind = Literal["compliance_desktop", "social_mobile_buyer"]

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)
SOCIAL_REFERER = "https://www.tiktok.com/"


@asynccontextmanager
async def browser_session() -> AsyncIterator[Browser]:
    """Launch a headless Chromium and guarantee clean shutdown."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=settings.headless)
        try:
            yield browser
        finally:
            await browser.close()


async def capture_persona(
    url: str,
    persona: PersonaKind,
    scan_id: str,
    artifacts_dir: Path,
) -> PersonaCapture:
    """Capture one persona view of ``url``.

    TODO(T2): open a fresh context (persona headers; viewport ALWAYS
    {1280x800}), navigate, then record:
      * persona_{a|b}.png screenshot + persona_{a|b}.html source -> artifacts_dir
      * all request hosts -> network_hosts
      * first request URL matching gateway|checkout|pay -> checkout_endpoint
      * billing_descriptor (page meta/JSON-LD convention — coordinate with T1)
      * detected_items (catalog tokens) and hidden-element bounding boxes
      * SHA-256 of saved HTML + PNG -> html_sha256 / screenshot_sha256
      * screenshot_url = "/artifacts/{scan_id}/persona_{a|b}.png"
    """
    raise NotImplementedError("T2 — implement per docs/TASKS.md")


async def capture_both_personas(
    url: str, scan_id: str, artifacts_dir: Path
) -> tuple[PersonaCapture, PersonaCapture]:
    """Capture Persona A and Persona B in parallel (asyncio.gather).

    TODO(T2): share one browser_session(); two isolated contexts.
    Returns (persona_a, persona_b).
    """
    raise NotImplementedError("T2 — implement per docs/TASKS.md")
