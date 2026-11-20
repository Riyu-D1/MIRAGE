/**
 * Minimal typed placeholder data — exists ONLY to verify UI compilation and
 * render component shells before T6 wires live data. Do not extend; the real
 * pipeline output replaces this (see docs/TASKS.md).
 */
import type { ScanResult } from "./types";

export const mockScan: ScanResult = {
  scan_id: "00000000-0000-0000-0000-000000000000",
  target_url: "http://localhost:8001/",
  created_at: "2026-01-01T00:00:00Z",
  verdict: "PENDING",
  reality_gap_score: 0,
  evidence_merkle_hash: "",
  persona_a: null,
  persona_b: null,
  divergence: null,
  injections: [],
  osint: null,
};
