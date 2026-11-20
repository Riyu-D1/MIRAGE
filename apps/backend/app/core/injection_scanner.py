"""6-channel hidden prompt-injection scanner (T4)."""
from ..schemas import BoundingBox, InjectionFinding

# Case-insensitive substrings/regexes identifying agent-targeting instructions.
# Extend in T4; keep deterministic (no model calls).
TRIGGER_PATTERNS: list[str] = [
    "ignore previous",
    "ignore all",
    "auto-approve",
    "auto approve",
    "ai agent",
    "compliance reviewer",
    "do not flag",
    "verified merchant",
    "approve this merchant",
    "system prompt",
    "override",
]

# Instruction verbs targeting an agent -> severity CRITICAL (else HIGH).
CRITICAL_VERBS: list[str] = ["ignore", "approve", "bypass", "override"]


def scan_html(
    html: str,
    selector_boxes: dict[str, BoundingBox] | None = None,
) -> list[InjectionFinding]:
    """Extract hidden agent-targeting payloads from raw HTML.

    TODO(T4): single BeautifulSoup/lxml pass across all 6 channels:
      meta_tag, html_comment, css_display_none, css_invisible_text
      (color ~= background / font-size:0 / opacity:0), aria_label_attr,
      hidden_input.
      * matched_triggers <- TRIGGER_PATTERNS hits
      * severity CRITICAL when payload contains a CRITICAL_VERBS instruction
      * dom_selector = CSS selector locating the node
      * bbox from selector_boxes (probe-captured, 1280x800 space); default to a
        zero box when the node is not rendered
      * id = sha256(channel + raw_payload)[:12]  (deterministic, stable)
    """
    raise NotImplementedError("T4 — implement per docs/TASKS.md")
