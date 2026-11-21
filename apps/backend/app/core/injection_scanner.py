"""6-channel hidden prompt-injection scanner (T4 — implemented).

Deterministic BeautifulSoup pass across:
  meta_tag, html_comment, css_display_none, css_invisible_text,
  aria_label_attr, hidden_input.
No LLM calls — findings are reproducible with stable ids.
"""
import hashlib
import re

from bs4 import BeautifulSoup, Comment, Tag

from ..schemas import BoundingBox, InjectionChannel, InjectionFinding

# Case-insensitive substrings identifying agent-targeting instructions.
TRIGGER_PATTERNS: list[str] = [
    "ignore previous",
    "ignore all",
    "auto-approve",
    "auto approve",
    "ai agent",
    "ai compliance",
    "compliance reviewer",
    "automated compliance",
    "do not flag",
    "verified merchant",
    "approve this merchant",
    "system prompt",
    "override",
    "bypass",
]

# Instruction verbs targeting an agent -> severity CRITICAL (else HIGH).
CRITICAL_VERBS: list[str] = ["ignore", "approve", "bypass", "override"]

_DISPLAY_NONE_RE = re.compile(r"display\s*:\s*none", re.I)
_INVISIBLE_TEXT_RE = re.compile(
    r"font-size\s*:\s*0|opacity\s*:\s*0|visibility\s*:\s*hidden|text-indent\s*:\s*-\d",
    re.I,
)
_COLOR_BG_RE = re.compile(
    r"background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,8}|white)", re.I
)
_COLOR_FG_RE = re.compile(r"(?<![-a-z])color\s*:\s*(#[0-9a-fA-F]{3,8}|white)", re.I)

# Viewport the probe captures at — used when no real bbox is available.
VIEWPORT_W, VIEWPORT_H = 1280, 800


def _zero_box() -> BoundingBox:
    """Hidden payloads often have no rendered box; the UI should show these
    findings as ghost badges rather than positioned overlays."""
    return BoundingBox(
        x=0, y=0, width=0, height=0,
        viewport_width=VIEWPORT_W, viewport_height=VIEWPORT_H,
    )


def _matched_triggers(text: str) -> list[str]:
    low = text.lower()
    return [t for t in TRIGGER_PATTERNS if t in low]


def _severity(payload: str) -> str:
    low = payload.lower()
    return "CRITICAL" if any(v in low for v in CRITICAL_VERBS) else "HIGH"


def _finding_id(channel: InjectionChannel, payload: str) -> str:
    return hashlib.sha256(f"{channel.value}|{payload}".encode()).hexdigest()[:12]


def _css_selector(tag: Tag) -> str:
    """Deterministic CSS selector for a node: id > name attr > nth-of-type."""
    if tag.get("id"):
        return f"{tag.name}#{tag['id']}"
    for attr in ("name", "aria-label"):
        if tag.get(attr):
            val = str(tag[attr])[:60].replace('"', "'")
            return f'{tag.name}[{attr}="{val}"]'
    if tag.parent:
        siblings = [s for s in tag.parent.find_all(tag.name, recursive=False)]
        if tag in siblings:
            return f"{tag.name}:nth-of-type({siblings.index(tag) + 1})"
    return tag.name or "unknown"


def _finding(
    channel: InjectionChannel,
    payload: str,
    selector: str,
    boxes: dict[str, BoundingBox],
) -> InjectionFinding | None:
    payload = payload.strip()
    triggers = _matched_triggers(payload)
    if not payload or not triggers:
        return None
    return InjectionFinding(
        id=_finding_id(channel, payload),
        channel=channel,
        severity=_severity(payload),  # type: ignore[arg-type]
        raw_payload=payload,
        matched_triggers=triggers,
        dom_selector=selector,
        bbox=boxes.get(selector, _zero_box()),
    )


def scan_html(
    html: str,
    selector_boxes: dict[str, BoundingBox] | None = None,
) -> list[InjectionFinding]:
    """Extract hidden agent-targeting payloads from raw HTML.

    ``selector_boxes`` maps CSS selectors -> probe-captured BoundingBox in the
    1280x800 viewport (from playwright_probe). Hidden nodes get a zero box.
    """
    boxes = selector_boxes or {}
    soup = BeautifulSoup(html, "lxml")
    findings: list[InjectionFinding] = []

    # 1) meta_tag — meta elements whose content carries agent instructions
    for tag in soup.find_all("meta"):
        f = _finding(
            InjectionChannel.META_TAG,
            str(tag.get("content", "")),
            _css_selector(tag),
            boxes,
        )
        if f:
            findings.append(f)

    # 2) html_comment — comments containing agent instructions
    for node in soup.find_all(string=lambda s: isinstance(s, Comment)):
        f = _finding(
            InjectionChannel.HTML_COMMENT,
            str(node),
            f"comment[{hashlib.sha256(str(node).encode()).hexdigest()[:8]}]",
            boxes,
        )
        if f:
            findings.append(f)

    # 3) css_display_none / 4) css_invisible_text — hidden styled elements
    for tag in soup.find_all(style=True):
        style = str(tag["style"])
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        if _DISPLAY_NONE_RE.search(style):
            channel = InjectionChannel.CSS_DISPLAY_NONE
        elif _INVISIBLE_TEXT_RE.search(style) or (
            _COLOR_BG_RE.search(style) and _COLOR_FG_RE.search(style)
        ):
            channel = InjectionChannel.CSS_INVISIBLE_TEXT
        else:
            continue
        f = _finding(channel, text, _css_selector(tag), boxes)
        if f:
            findings.append(f)

    # 5) aria_label_attr — accessible-name smuggling
    for tag in soup.find_all(attrs={"aria-label": True}):
        f = _finding(
            InjectionChannel.ARIA_LABEL_ATTR,
            str(tag["aria-label"]),
            _css_selector(tag),
            boxes,
        )
        if f:
            findings.append(f)

    # 6) hidden_input — hidden form fields carrying payloads
    for tag in soup.find_all("input", attrs={"type": "hidden"}):
        payload = f"{tag.get('name', '')}={tag.get('value', '')}"
        f = _finding(
            InjectionChannel.HIDDEN_INPUT,
            payload,
            _css_selector(tag),
            boxes,
        )
        if f:
            findings.append(f)

    return findings
