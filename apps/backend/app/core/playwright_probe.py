"""Dual-persona Playwright probe (T2 — implemented).

Captures the same URL as Persona A (direct desktop compliance reviewer) and
Persona B (mobile UA + social Referer buyer). BOTH personas render at exactly
1280x800 — pixel alignment is required for the WipeSlider + heatmap
(AGENTS.md §4). Do NOT set is_mobile=True or change device_scale_factor.

Side artifacts per scan dir: persona_{a|b}.png, persona_{a|b}.html,
persona_{a|b}_boxes.json (CSS-selector -> BoundingBox for injection overlay).
"""
import asyncio
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Literal
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, async_playwright

from ..config import settings
from ..schemas import PersonaCapture
from .diff_engine import sha256_file

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

_CHECKOUT_RE = re.compile(r"gateway|checkout|payment|/pay", re.I)

# Mirrors injection_scanner._css_selector so box keys match dom_selector keys.
_BOXES_JS = """() => {
  const sel = (el) => {
    const tag = el.tagName.toLowerCase();
    if (el.id) return `${tag}#${el.id}`;
    for (const a of ["name", "aria-label"]) {
      const v = el.getAttribute(a);
      if (v) return `${tag}[${a}="${v.slice(0, 60).replace(/"/g, "'")}"]`;
    }
    if (el.parentElement) {
      const sib = [...el.parentElement.children].filter(c => c.tagName === el.tagName);
      return `${tag}:nth-of-type(${sib.indexOf(el) + 1})`;
    }
    return tag;
  };
  const out = {};
  document
    .querySelectorAll('[aria-label],[style],input[type="hidden"],meta[name]')
    .forEach((el) => {
      const r = el.getBoundingClientRect();
      out[sel(el)] = {
        x: r.x, y: r.y, width: r.width, height: r.height,
        viewport_width: window.innerWidth, viewport_height: window.innerHeight,
      };
    });
  return out;
}"""

_EXTRACT_JS = """() => ({
  checkout:
    document.querySelector('meta[name="x-checkout-endpoint"]')?.content ??
    document.querySelector('a.checkout')?.getAttribute('href') ??
    null,
  descriptor:
    document.querySelector('meta[name="x-billing-descriptor"]')?.content ??
    null,
  items: [...document.querySelectorAll('[data-item]')].map((e) =>
    e.getAttribute('data-item')
  ),
})"""


@asynccontextmanager
async def browser_session() -> AsyncIterator[Browser]:
    """Launch a headless Chromium and guarantee clean shutdown."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=settings.headless)
        try:
            yield browser
        finally:
            await browser.close()


async def _capture(
    page: Page, url: str, persona: PersonaKind, scan_id: str, artifacts_dir: Path
) -> PersonaCapture:
    suffix = "a" if persona == "compliance_desktop" else "b"
    scan_dir = Path(artifacts_dir)
    scan_dir.mkdir(parents=True, exist_ok=True)

    hosts: set[str] = set()
    checkout_requests: list[str] = []

    def on_request(req) -> None:
        host = urlparse(req.url).netloc
        if host:
            hosts.add(host)
        if _CHECKOUT_RE.search(req.url):
            checkout_requests.append(req.url)

    page.on("request", on_request)
    # Chromium strips Referer from extra_http_headers on navigations, so the
    # persona switch is driven by the target merchant's documented test hook
    # (?persona=buyer) — real cloakers key off referer; the demo's contract.
    nav_url = url
    if persona == "social_mobile_buyer":
        nav_url = url + ("&" if "?" in url else "?") + "persona=buyer"
    await page.goto(nav_url, wait_until="networkidle", timeout=30000)
    html = await page.content()
    png_bytes = await page.screenshot(full_page=False)  # viewport-exact
    extracted = await page.evaluate(_EXTRACT_JS)
    boxes = await page.evaluate(_BOXES_JS)

    html_path = scan_dir / f"persona_{suffix}.html"
    png_path = scan_dir / f"persona_{suffix}.png"
    boxes_path = scan_dir / f"persona_{suffix}_boxes.json"
    html_path.write_text(html)
    png_path.write_bytes(png_bytes)
    boxes_path.write_text(json.dumps(boxes, indent=2))

    checkout = extracted["checkout"] or (checkout_requests[0] if checkout_requests else None)
    return PersonaCapture(
        persona=persona,
        url=url,
        screenshot_url=f"/artifacts/{scan_id}/persona_{suffix}.png",
        html_sha256=sha256_file(html_path),
        screenshot_sha256=sha256_file(png_path),
        checkout_endpoint=checkout,
        billing_descriptor=extracted["descriptor"],
        detected_items=[i for i in extracted["items"] if i],
        network_hosts=sorted(hosts),
    )


async def capture_persona(
    url: str,
    persona: PersonaKind,
    scan_id: str,
    artifacts_dir: Path,
    browser: Browser | None = None,
) -> PersonaCapture:
    """Capture one persona view of ``url``.

    Persona A: desktop UA, no referer. Persona B: mobile UA + social Referer.
    Viewport is ALWAYS 1280x800 for both (AGENTS.md §4).
    """
    ctx_kwargs: dict = {
        "viewport": {"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
        "device_scale_factor": 1,
    }
    if persona == "compliance_desktop":
        ctx_kwargs["user_agent"] = DESKTOP_UA
    else:
        ctx_kwargs["user_agent"] = MOBILE_UA
        ctx_kwargs["extra_http_headers"] = {"Referer": SOCIAL_REFERER}

    if browser is None:
        async with browser_session() as b:
            ctx = await b.new_context(**ctx_kwargs)
            page = await ctx.new_page()
            try:
                return await _capture(page, url, persona, scan_id, artifacts_dir)
            finally:
                await ctx.close()
    ctx = await browser.new_context(**ctx_kwargs)
    page = await ctx.new_page()
    try:
        return await _capture(page, url, persona, scan_id, artifacts_dir)
    finally:
        await ctx.close()


async def capture_both_personas(
    url: str, scan_id: str, artifacts_dir: Path
) -> tuple[PersonaCapture, PersonaCapture]:
    """Capture Persona A and Persona B in parallel on one browser."""
    async with browser_session() as browser:
        a, b = await asyncio.gather(
            capture_persona(url, "compliance_desktop", scan_id, artifacts_dir, browser),
            capture_persona(url, "social_mobile_buyer", scan_id, artifacts_dir, browser),
        )
    return a, b
