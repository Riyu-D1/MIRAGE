/**
 * MIRAGE locked data contracts (TypeScript).
 *
 * SINGLE SOURCE OF TRUTH — mirrored 1-to-1 by apps/backend/app/schemas.py.
 * Never rename/retype a field without updating BOTH files. See AGENTS.md §3.
 */

export type Verdict =
  | "CLOAKED_CRITICAL"
  | "INJECTION_DETECTED"
  | "DRIFT_DETECTED"
  | "VERIFIED_CLEAN"
  | "PENDING";

export type InjectionChannel =
  | "meta_tag"
  | "html_comment"
  | "css_display_none"
  | "css_invisible_text"
  | "aria_label_attr"
  | "hidden_input";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
  viewport_width: number;
  viewport_height: number;
}

export interface InjectionFinding {
  id: string;
  channel: InjectionChannel;
  severity: "HIGH" | "CRITICAL";
  raw_payload: string;
  matched_triggers: string[];
  dom_selector: string;
  bbox: BoundingBox;
}

export type Persona = "compliance_desktop" | "social_mobile_buyer";

export interface PersonaCapture {
  persona: Persona;
  url: string;
  screenshot_url: string;
  html_sha256: string;
  screenshot_sha256: string;
  checkout_endpoint: string | null;
  billing_descriptor: string | null;
  detected_items: string[];
  network_hosts: string[];
}

export interface DivergenceReport {
  checkout_swapped: boolean;
  descriptor_swapped: boolean;
  claimed_gateway: string | null;
  buyer_gateway: string | null;
  claimed_descriptor: string | null;
  buyer_descriptor: string | null;
  text_jaccard_distance: number;
  pixel_divergence_pct: number;
  heatmap_url: string | null;
  compliance_only_items: string[];
  buyer_only_items: string[];
  compute_ms: number;
}

export interface AdverseMediaHit {
  title: string;
  url: string;
  snippet: string;
}

export interface CovertOutreachLog {
  sender: string;
  status: string;
  transcript: string;
}

export interface OsintSummary {
  source_mode: "live" | "cached_fallback";
  company_name: string | null;
  company_number: string | null;
  address_shell_density: number | null;
  adverse_media_hits: AdverseMediaHit[];
  covert_outreach_log: CovertOutreachLog | null;
}

export interface ScanResult {
  scan_id: string;
  target_url: string;
  created_at: string;
  verdict: Verdict;
  reality_gap_score: number;
  evidence_merkle_hash: string;
  persona_a: PersonaCapture | null;
  persona_b: PersonaCapture | null;
  divergence: DivergenceReport | null;
  injections: InjectionFinding[];
  osint: OsintSummary | null;
}

export type AgentEventStatus = "running" | "done" | "alert" | "error";

export interface AgentEvent {
  id: string;
  scan_id: string;
  timestamp: string;
  step: string;
  agent: string;
  status: AgentEventStatus;
  detail: string;
  latency_ms: number | null;
}

export interface ReplayCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export type HashIntegrity = "EXACT_MATCH" | "MISMATCH";

export interface ReplayVerification {
  scan_id: string;
  verified: boolean;
  llm_calls: number;
  elapsed_ms: number;
  hash_integrity: HashIntegrity;
  checks: ReplayCheck[];
}

export interface SleeperCheckResult {
  target_url: string;
  day: number;
  intact: boolean;
  baseline_hash: string;
  current_hash: string;
  baseline_gateway: string;
  current_gateway: string;
  alert_triggered: boolean;
  screenshot_url: string | null;
}

/* ── Request payloads ── */

export interface ScanRequest {
  url: string;
}

export interface SleeperRegisterRequest {
  target_url: string;
}

export interface SleeperSimulateRequest {
  target_url: string;
  day: number;
}

export interface HealthStatus {
  status: string;
  service: string;
  integrations: Record<string, boolean>;
}
