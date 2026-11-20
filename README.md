# MIRAGE — Merchant X-Ray & KYB Lie-Detector

> Visual, adversarial merchant forensics for payment acquirers and compliance teams.
> Built for a 6-hour financial-crime hackathon. **Agents: read `AGENTS.md` first.**

MIRAGE catches deceptive e-commerce merchants committing **transaction laundering**
by answering one question: *does the merchant show the compliance team a different
storefront than it shows a real buyer — and is it trying to manipulate the AI doing
the checking?*

## The 5 Capabilities

1. **Lens A vs. Lens B — Dual-Persona Cloaking.** The same merchant URL is probed as
   a direct desktop compliance reviewer vs. a mobile/social-referrer buyer. Swapped
   storefronts, hidden checkout-gateway redirects, and mismatched billing
   descriptors are exposed and scored (`reality_gap_score`, 0–100).
2. **Lens C — Prompt-Injection X-Ray.** Hidden HTML/DOM channels (`<meta>`, HTML
   comments, `display:none`, white-on-white CSS, `aria-label`, `<input type=hidden>`)
   are scanned for embedded instructions trying to manipulate AI compliance
   reviewers into auto-approving the merchant.
3. **Sleeper Watch — Day 1 → Day 60 Drift.** Approved merchant DOMs/checkouts are
   hashed at onboarding; a Grok Bot Routine re-checks them to catch post-approval
   bait-and-switch swaps.
4. **Zero-LLM Regulator Replay.** Raw captured artifacts (HTML, HAR/checkout
   endpoints, screenshots, hashes) are re-verified purely deterministically —
   `0 LLM calls` — backed by an immutable Supabase evidence vault.
5. **Visual-First Mission Control.** Interactive 3-Lens Reality Split, draggable
   before/after X-Ray Wipe Slider with pixel-diff heatmap overlay, crimson DOM
   bounding boxes over rendered screenshots, animated SVG Payment-Rail Fork,
   Day 1 → Day 60 timeline scrubber, and a live SSE mission feed.

## Quickstart

```powershell
# Windows
scripts\setup.ps1   # one-time: venv, deps, Playwright Chromium, npm install
scripts\dev.ps1     # boots target (8001), backend (8000), web (3000)
```

```bash
# macOS / Linux
bash scripts/setup.sh
bash scripts/dev.sh
```

Then open **http://localhost:3000**.

Verify everything is healthy:

```bash
pytest tests/          # from repo root — smoke suite
cd apps/web && npm run build
```

## Repository Map

| Path                     | What lives here                                            |
| ------------------------ | ---------------------------------------------------------- |
| `AGENTS.md`              | Agent operating manual — **read first**                    |
| `docs/`                  | Architecture, build tickets (T1–T10), design system, demo checklist |
| `apps/backend/`          | FastAPI API + deterministic forensics core (port 8000)     |
| `apps/web/`              | Next.js 15 Mission Control UI (port 3000)                  |
| `apps/target-merchant/`  | Self-hosted demo merchant — cloaked + clean control (8001) |
| `apps/mcp-server/`       | FastMCP tools for Grok Bot (port 8002)                     |
| `supabase/migrations/`   | Postgres schema + Realtime publication                     |
| `grokbot/`               | 10:30 AM activation checklist, Skill & Routine templates   |
| `extras/forgelab/`       | Backup pivot: PDF 4-layer forensics stub                   |
| `scripts/`               | Setup & dev launchers (PowerShell + Bash)                  |
| `tests/`                 | Pytest smoke suite                                         |

## Sponsor Stack (wired at 10:30 AM)

Grok Bot (Skills, Routines, Webhooks, MCP) · Supabase (Postgres + Realtime + MCP) ·
Tavily (live OSINT) · UK Companies House API. All optional — MIRAGE runs fully
offline with SQLite + cached fixtures. Paste keys into `.env` (see `.env.example`).

## Status

Starter blueprint: every module compiles, boots, and passes smoke tests; feature
logic is intentionally stubbed behind `TODO(T#)` tags mapped to `docs/TASKS.md`.
