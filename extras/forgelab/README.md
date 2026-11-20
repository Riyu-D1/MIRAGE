# ForgeLab — Backup Audible (PDF 4-Layer Forensics)

**When to pivot here:** only if the hackathon track skews toward *document/PDF
verification* instead of live-merchant cloaking (e.g., judges emphasize forged
KYB PDFs, bank statements, or invoices over storefront laundering). MIRAGE's
core stays the same — deterministic, hashed, zero-LLM — this module just
swaps the *subject* from a storefront to a PDF.

## The 4 Layers

| Layer | Check                                                          | Status in `analyzer_stub.py` |
| ----- | -------------------------------------------------------------- | ---------------------------- |
| 1     | Metadata forensics (producer, timestamps, XMP inconsistencies) | Typed stub — `check_metadata`|
| 2     | Font/encoding anomalies (embedded font subsets, ToUnicode gaps)| TODO                         |
| 3     | Visual/object-layer tampering (incremental updates, overlays)  | TODO                         |
| 4     | Running-balance / arithmetic re-derivation for statements      | Typed stub — `check_running_balance` |

## How to pivot (≤30 min)

1. Implement `analyzer_stub.py` (same determinism contract as `apps/backend/app/core/`:
   SHA-256 evidence, `perf_counter()` latencies, no LLM).
2. Expose it as a backend route (`POST /api/pdf/analyze`) following
   `routes/scans.py` patterns.
3. Reuse the Mission Control shell — swap ThreeLensStage content for the
   layer table + RegulatorReplayBar stays identical (dossier story unchanged).
