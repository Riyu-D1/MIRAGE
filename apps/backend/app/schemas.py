"""MIRAGE locked data contracts (Pydantic v2).

SINGLE SOURCE OF TRUTH — mirrored 1-to-1 by apps/web/src/lib/types.ts.
Never rename/retype a field without updating BOTH files. See AGENTS.md §3.
"""
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    CLOAKED_CRITICAL = "CLOAKED_CRITICAL"
    INJECTION_DETECTED = "INJECTION_DETECTED"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    VERIFIED_CLEAN = "VERIFIED_CLEAN"
    PENDING = "PENDING"


class InjectionChannel(str, Enum):
    META_TAG = "meta_tag"
    HTML_COMMENT = "html_comment"
    CSS_DISPLAY_NONE = "css_display_none"
    CSS_INVISIBLE_TEXT = "css_invisible_text"
    ARIA_LABEL_ATTR = "aria_label_attr"
    HIDDEN_INPUT = "hidden_input"


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float
    viewport_width: float
    viewport_height: float


class InjectionFinding(BaseModel):
    id: str
    channel: InjectionChannel
    severity: Literal["HIGH", "CRITICAL"]
    raw_payload: str
    matched_triggers: list[str] = Field(default_factory=list)
    dom_selector: str
    bbox: BoundingBox


class PersonaCapture(BaseModel):
    persona: Literal["compliance_desktop", "social_mobile_buyer"]
    url: str
    screenshot_url: str
    html_sha256: str
    screenshot_sha256: str
    checkout_endpoint: Optional[str] = None
    billing_descriptor: Optional[str] = None
    detected_items: list[str] = Field(default_factory=list)
    network_hosts: list[str] = Field(default_factory=list)


class DivergenceReport(BaseModel):
    checkout_swapped: bool
    descriptor_swapped: bool
    claimed_gateway: Optional[str] = None
    buyer_gateway: Optional[str] = None
    claimed_descriptor: Optional[str] = None
    buyer_descriptor: Optional[str] = None
    text_jaccard_distance: float
    pixel_divergence_pct: float
    heatmap_url: Optional[str] = None
    compliance_only_items: list[str] = Field(default_factory=list)
    buyer_only_items: list[str] = Field(default_factory=list)
    compute_ms: float


class AdverseMediaHit(BaseModel):
    title: str
    url: str
    snippet: str


class CovertOutreachLog(BaseModel):
    sender: str
    status: str
    transcript: str


class OsintSummary(BaseModel):
    source_mode: Literal["live", "cached_fallback"]
    company_name: Optional[str] = None
    company_number: Optional[str] = None
    address_shell_density: Optional[float] = None
    adverse_media_hits: list[AdverseMediaHit] = Field(default_factory=list)
    covert_outreach_log: Optional[CovertOutreachLog] = None


class ScanResult(BaseModel):
    scan_id: str
    target_url: str
    created_at: str
    verdict: Verdict
    reality_gap_score: int
    evidence_merkle_hash: str
    persona_a: Optional[PersonaCapture] = None
    persona_b: Optional[PersonaCapture] = None
    divergence: Optional[DivergenceReport] = None
    injections: list[InjectionFinding] = Field(default_factory=list)
    osint: Optional[OsintSummary] = None


class AgentEvent(BaseModel):
    id: str
    scan_id: str
    timestamp: str
    step: str
    agent: str
    status: Literal["running", "done", "alert", "error"]
    detail: str
    latency_ms: Optional[float] = None


class ReplayCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class ReplayVerification(BaseModel):
    scan_id: str
    verified: bool
    llm_calls: int
    elapsed_ms: float
    hash_integrity: Literal["EXACT_MATCH", "MISMATCH"]
    checks: list[ReplayCheck] = Field(default_factory=list)


class SleeperCheckResult(BaseModel):
    target_url: str
    day: int
    intact: bool
    baseline_hash: str
    current_hash: str
    baseline_gateway: str
    current_gateway: str
    alert_triggered: bool
    screenshot_url: Optional[str] = None


# ── Request payloads ─────────────────────────────────────────────────────────
class ScanRequest(BaseModel):
    url: str


class SleeperRegisterRequest(BaseModel):
    target_url: str


class SleeperSimulateRequest(BaseModel):
    target_url: str
    day: int = 60


class HealthStatus(BaseModel):
    status: str
    service: str
    integrations: dict[str, bool] = Field(default_factory=dict)
