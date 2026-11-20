# MIRAGE — Architecture

## System Diagram

```
                        ┌────────────────────────────────────────────┐
                        │        Mission Control UI (Next.js)         │
                        │          http://localhost:3000              │
                        │  ThreeLensStage · WipeSlider · InjectionOverlay
                        │  PaymentRailFork · SleeperTimeline · MissionRail
                        └───────────────┬────────────────────────────┘
                                        │ REST + SSE (/api/scans/{id}/stream)
                                        ▼
┌──────────────┐  MCP tools   ┌────────────────────────────────────────────┐
│  mcp-server  │─────────────▶│        Backend API + Forensics (FastAPI)    │
│  :8002       │  HTTP        │          http://localhost:8000              │
└──────┬───────┘              │                                            │
       ▲                      │  routes/   scans · sleeper · webhooks      │
       │ tool calls           │  core/     playwright_probe · diff_engine  │
   Grok Bot                   │            injection_scanner · sleeper_watch│
 (Cloud VM, Skills,           │            replay_engine                   │
  Routines, Webhooks)         │  integrations/ supabase · grokbot · osint  │
       ▲                      └───┬───────────┬──────────────┬─────────────┘
       │ inbound webhook          │ probes    │ persists     │ OSINT lookups
       │ (/api/webhooks/grokbot)  ▼           ▼              ▼
       └─────────────────  Target Merchant   Supabase ──or── SQLite    Companies House / Tavily
                           :8001 (demo)      Postgres+Realtime (fallback)   (live ──or── fixtures)
```

## Port Map

| Port | Service             | Key routes                                                        |
| ---- | ------------------- | ----------------------------------------------------------------- |
| 3000 | `apps/web`          | `/` Mission Control                                               |
| 8000 | `apps/backend`      | `/api/health` · `/api/scans` · `/api/scans/{id}/stream` (SSE) · `/api/scans/{id}/replay` · `/api/scans/{id}/dossier` · `/api/sleeper/*` · `/api/webhooks/grokbot` · `/artifacts/*` (static) |
| 8001 | `apps/target-merchant` | `/health` · `/` (cloaked) · `/control` · `/sleeper?day=N` · `/mock-gateway/*` |
| 8002 | `apps/mcp-server`   | FastMCP tools: `mirage_scan`, `mirage_replay`, `mirage_sleeper_check`, `mirage_dossier` |

## Data Flow (one scan)

1. `POST /api/scans {url}` → creates `ScanResult(scan_id, verdict=PENDING)`, kicks async pipeline, returns `scan_id`.
2. Pipeline emits `AgentEvent`s → persisted (Supabase/SQLite) → pushed on SSE stream.
3. `playwright_probe` captures Persona A (direct desktop) + Persona B (mobile UA, social Referer), both at **1280×800** → PNG screenshots, raw HTML, network/checkout requests, DOM bounding boxes → saved under `artifacts/{scan_id}/` with SHA-256 manifests.
4. `diff_engine` computes checkout/descriptor diffs, catalog Jaccard distance, pixel-diff `heatmap.png`, `reality_gap_score`.
5. `injection_scanner` extracts hidden payloads across 6 channels → `InjectionFinding[]` with bounding boxes.
6. `osint_client` enriches with Companies House + Tavily (live or cached fixtures).
7. `ScanResult` finalized → verdict → Supabase/SQLite → SSE `done` event → UI renders.
8. `POST /api/scans/{id}/replay` → `replay_engine` re-verifies stored artifacts with **0 LLM calls** → `ReplayVerification`.
9. `GET /api/scans/{id}/dossier` → printable HTML/JSON evidence dossier.

## Offline-First + Sponsor Upgrade Strategy

Everything runs **fully offline**; sponsor keys upgrade behavior in place:

| Layer      | Offline default                          | With sponsor key                          |
| ---------- | ---------------------------------------- | ----------------------------------------- |
| Persistence| SQLite at `artifacts/mirage.db`           | Supabase Postgres (`supabase/migrations/001_initial_schema.sql`) |
| Live push  | SSE from in-process event bus            | Same SSE + Supabase Realtime for multi-client |
| Agent feed | `agent_events` written locally            | Also dispatched to `GROKBOT_WEBHOOK_URL`   |
| OSINT      | Fixtures in `integrations/fixtures/`      | Tavily + Companies House live calls        |
| Sleeper    | `/api/sleeper/simulate?day=N` manual      | Grok Bot Routine calls MCP on a schedule   |

`app/config.py` computes `*_enabled` flags; `/api/health` reports them; the UI shows
them as health pills. **No code path may hard-require a sponsor key.**

## Determinism Contract

- Every artifact on disk is hashed SHA-256; hashes live in `PersonaCapture`,
  `evidence_artifacts`, and the evidence Merkle hash (`evidence_merkle_hash`).
- All timings via `time.perf_counter()`; reported in `*_ms` fields.
- `replay_engine` re-derives verdicts from stored artifacts only — it must never
  call the network, an LLM, or the probe.

## Frontend ↔ Backend Boundary

- REST: `apps/web/src/lib/api.ts` → `NEXT_PUBLIC_API_URL/api/*`.
- SSE: `useScanStream(scanId)` hook → `GET /api/scans/{id}/stream` emitting
  `AgentEvent` JSON lines.
- Contracts: `app/schemas.py` ⇔ `src/lib/types.ts` — identical field names, always.
- Screenshots/heatmaps served from `BACKEND_URL/artifacts/{scan_id}/...`; frontend
  stores only the relative `*_url` path and resolves it via `api.ts`.
