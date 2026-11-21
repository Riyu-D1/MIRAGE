# AGENTS.md — MIRAGE Agent Operating Manual

> **READ THIS FILE FIRST.** This is the single entry point for any autonomous coding
> agent (Grok Bot, Cursor, Claude Code, Devin) working on MIRAGE. Read it fully,
> then read `docs/TASKS.md` and execute tickets `T1` → `T10`.

---

## 1. Project Identity

**MIRAGE** is a visual, adversarial **Merchant X-Ray & KYB Lie-Detector** for payment
acquirers and compliance teams. It catches deceptive e-commerce merchants committing
transaction laundering by comparing what a merchant shows a **compliance reviewer**
vs. what it shows a **real buyer**, and by scanning for **prompt injections hidden in
the DOM** aimed at AI reviewers.

### Core Rule — Determinism Over Guesswork

**Never replace deterministic Python forensics with LLM guesswork.** Every detection
must output:

- **Reproducible evidence** (raw HTML, screenshots, network logs stored as artifacts),
- **SHA-256 hashes** of every captured artifact,
- **Exact elapsed latency in ms** (`compute_ms` / `latency_ms` / `elapsed_ms`) measured
  with `time.perf_counter()`.

The Regulator Replay endpoint re-verifies verdicts with **0 LLM calls**. If a check
cannot be made deterministic, flag it in code with `# NONDETERMINISTIC:` and surface
it in the evidence dossier.

---

## 2. Architecture & Port Map

| Service                | Path                    | URL                     | Purpose                                        |
| ---------------------- | ----------------------- | ----------------------- | ---------------------------------------------- |
| Mission Control UI     | `apps/web`              | http://localhost:3000   | Next.js 15 App Router demo dashboard           |
| Backend API + Forensics| `apps/backend`          | http://localhost:8000   | FastAPI; serves artifacts at `/artifacts/*`    |
| Target Merchant (demo) | `apps/target-merchant`  | http://localhost:8001   | Self-hosted cloaked merchant + clean control   |
| MCP Server             | `apps/mcp-server`       | http://localhost:8002   | FastMCP tools exposing MIRAGE to Grok Bot      |

Request flow:

```
Browser (3000) ──REST/SSE──> Backend (8000) ──probes──> Target Merchant (8001)
                                  │
                                  ├──> Supabase (Postgres + Realtime) or SQLite fallback
                                  ├──> Grok Bot webhook (if GROKBOT_WEBHOOK_URL set)
                                  └──> OSINT: Companies House / Tavily (or fixtures)

Grok Bot ──MCP──> mcp-server (8002) ──HTTP──> Backend (8000)
```

Full data flow, offline-first strategy, and the sponsor upgrade path are documented
in `docs/ARCHITECTURE.md`.

---

## 3. Strict Contract Rule

`apps/backend/app/schemas.py` (Pydantic v2) and `apps/web/src/lib/types.ts`
(TypeScript) are the **single source of truth** for every payload crossing the
REST/SSE boundary. They mirror each other **1-to-1**.

- **Never** rename, retype, or delete a field in one file without making the
  identical change in the other.
- Optional in TS (`| null`) == `Optional[...] = None` in Python.
- Enum string values must match character-for-character.
- `tests/test_smoke.py` serializes every schema — a contract drift fails CI.

When adding a field: add it to `schemas.py`, then `types.ts`, then regenerate any
mock in `apps/web/src/lib/mockData.ts`.

---

## 4. Pixel Alignment Rule (Crucial for Visuals)

Both Persona A and Persona B Playwright captures **MUST render at the exact same
viewport dimensions: `1280 × 800`** — even though Persona B sends a **mobile
User-Agent + social Referer** headers. The viewport stays `1280×800` for BOTH.

This guarantees pixel-exact alignment for:

- the frontend **X-Ray Wipe Slider** (before/after image comparison), and
- the **pixel-diff heatmap** overlay produced by `core/diff_engine.py`.

Any `BoundingBox` returned in an `InjectionFinding` is in this same `1280×800`
coordinate space (`viewport_width`/`viewport_height` fields record it explicitly).
Do **not** use `device_scale_factor` or `is_mobile=True` — they change layout
metrics and break overlay registration.

---

## 5. Offline-First Graceful Degradation Rule

Every external sponsor integration activates **automatically when its key is present
in `.env`** and **gracefully falls back** when absent or unreachable:

| Env var                       | When set                          | When absent / offline              |
| ----------------------------- | --------------------------------- | ---------------------------------- |
| `SUPABASE_URL` + keys         | Postgres + Realtime persistence   | Local SQLite (`artifacts/mirage.db`)|
| `GROKBOT_WEBHOOK_URL`         | Live webhook dispatch to Grok Bot | Events logged to `agent_events` only |
| `TAVILY_API_KEY`              | Live adverse-media OSINT          | Cached fixtures (`integrations/fixtures/`) |
| `COMPANIES_HOUSE_API_KEY`     | Live company lookup               | Cached fixtures                    |

`app/config.py` exposes `settings.supabase_enabled`, `settings.grokbot_enabled`,
`settings.tavily_enabled`, `settings.companies_house_enabled`. Check the flag —
never try/except your way to detection. `/api/health` reports every flag so the
frontend health pills stay truthful.

**A feature must never hard-fail because a sponsor key is missing.** The demo must
run fully offline.

---

## 6. Repository Layout

See `docs/ARCHITECTURE.md` for the annotated tree. In short:

- `apps/backend/app/core/` — deterministic forensics modules (probes, diff, injection, sleeper, replay)
- `apps/backend/app/integrations/` — sponsor client shells (supabase, grokbot, osint)
- `apps/backend/app/routes/` — REST + SSE route stubs
- `apps/web/src/components/` — typed visual component shells (`TODO(T8/T9)`)
- `supabase/migrations/` — SQL to paste into Supabase SQL Editor at 10:30 AM
- `grokbot/` — morning activation checklist + Skill/Routine paste-ready templates
- `tests/test_smoke.py` — smoke suite; keep it green
- `scripts/` — `setup.ps1`/`dev.ps1` (Windows) and `setup.sh`/`dev.sh` (macOS/Linux)

## 7. Implementation Status (pre-built — verify, don't redo)

Already working end-to-end (see `docs/TASKS.md` status table):

- **T1–T4 done** — target merchant (persona split, 6 injections, sleeper days,
  mock gateways), Playwright dual-persona probe @1280×800, divergence diff +
  neon heatmap + reality-gap score, 6-channel injection scanner.
- **T5 mostly done** — `check_drift`, sleeper routes, `sleeper_monitors`
  persistence (+`GET /api/sleeper/monitors`), `replay_engine` (0-LLM
  EXACT_MATCH), and the printable HTML dossier (`?format=html`) are all live.
  Remaining: Routine scheduling, `screenshot_url` on checks.
- **T6 mostly done** — `POST /api/scans` returns PENDING instantly and runs
  the pipeline in a background thread; `GET /scans/{id}/stream` is a LIVE SSE
  feed (paced replay + tail-poll until `pipeline.complete`). Clients refetch
  the scan on terminal (see page.tsx). EvidenceStore covers SQLite AND
  Supabase paths (auto-fallback on bad keys); webhook dispatch + inbound
  `/api/webhooks/grokbot` injection into the event feed both work. Proven:
  `:8001/` → `CLOAKED_CRITICAL` (gap 80, 6 injections, both swaps);
  `/control` → `VERIFIED_CLEAN`. Remaining: Realtime client in web.
- **T7 partial** — all 4 MCP tools call the backend with contract checks and
  `mirage_scan` polls to completion.
- **Gotcha:** Chromium strips `Referer` on navigations — Persona B switches via
  the merchant's `?persona=buyer` test hook (documented in playwright_probe.py).

**Next tickets for the agent: T8/T9 frontend visuals — the big remaining
chunk (gauge animation, X-Ray polish, payment-rail animation, live stepper
states are already fed by the live SSE feed) → T10 E2E → T5/T6 leftovers
(Routine scheduling, Realtime).**

## 8. How to Start Building (Saturday 11:00 AM)

1. Run `scripts/setup.ps1` (Windows) or `scripts/setup.sh` (macOS/Linux) if not already done.
2. Run `scripts/dev.ps1` / `scripts/dev.sh` — verify all four health endpoints respond.
3. Open `docs/TASKS.md`. Execute tickets **in order T1 → T10**. T1–T5 are backend;
   T6–T7 are integration; T8–T9 are frontend; T10 is end-to-end verification.
   Tickets marked `[parallel-safe]` touch disjoint files and may be done concurrently
   by sub-agents.
4. After **each** milestone: `pytest tests/` from repo root AND `npm run build` in
   `apps/web`. Do not start the next ticket on a red build.
5. Keep every function's declared signature stable — the stubs' signatures are the
   contract with the rest of the system. Fill in bodies; don't redesign interfaces.
6. Honor every `# TODO(T#)` tag — it maps 1:1 to a ticket in `docs/TASKS.md`.

## 9. Hard Don'ts

- Don't commit `.env`, `node_modules/`, `.venv/`, `artifacts/` output, or secrets.
- Don't add dependencies without pinning versions in `requirements.txt` / `package.json`.
- Don't call an LLM inside `core/` forensic modules — they are the deterministic core.
- Don't change the `1280×800` viewport, schema field names, or port assignments.
- Don't swallow exceptions silently — log with latency + artifact hash context.
