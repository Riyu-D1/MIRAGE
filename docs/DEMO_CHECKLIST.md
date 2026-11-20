# MIRAGE — Demo Checklist

## 10:30 AM — Activation (see `grokbot/ACTIVATE_AT_1030.md` for detail)

- [ ] `.env` populated: Supabase URL + both keys, `GROKBOT_WEBHOOK_URL`,
      `GROKBOT_API_KEY`, `TAVILY_API_KEY`, `COMPANIES_HOUSE_API_KEY`
- [ ] `supabase/migrations/001_initial_schema.sql` pasted into Supabase SQL Editor and run
- [ ] Grok Bot Skill + Routine created from `grokbot/*.template.md`
- [ ] `scripts/dev.ps1` / `dev.sh` up: all 4 ports healthy, `/api/health` flags green
- [ ] `pytest tests/` green · `npm run build` clean

## 15:00 Office-Hours Checklist

- [ ] Full scan of `http://localhost:8001/` completes < ~15s with live SSE feed
- [ ] Scan of `http://localhost:8001/control` returns `VERIFIED_CLEAN` (0 false positives)
- [ ] Sleeper day=60 simulation triggers drift alert
- [ ] `/replay` returns `EXACT_MATCH`, `llm_calls=0`
- [ ] Stage QR scans to the target on a phone
- [ ] Grok Bot Routine has fired at least once OR manual MCP tool call demoed
- [ ] Video recorded (see below) + uploaded
- [ ] Repo pushed, README quickstart verified on a clean machine state

## 75-Second Video Triage Shotlist

| # | Sec | Shot                                                              |
| - | --- | ---------------------------------------------------------------- |
| 1 | 0–8  | Cold open: Mission Control, paste `localhost:8001`, hit SCAN     |
| 2 | 8–20 | MissionRail live SSE steps ticking with latencies                |
| 3 | 20–35| ThreeLensStage lands: WipeSlider drag reveals swapped storefront  |
| 4 | 35–50| InjectionOverlay: click crimson boxes, show payloads             |
| 5 | 50–58| PaymentRailFork: declared vs hijacked gateway animation          |
| 6 | 58–66| SleeperTimeline scrub Day 1→60 → fracture alert                  |
| 7 | 66–75| RegulatorReplayBar: "0 LLM CALLS · EXACT MATCH · Nms" + dossier  |

## 180-Second Stage Flow

1. **Hook (0–20s):** "This merchant passed KYB. It's laundering transactions.
   Watch us prove it in 15 seconds." Run live scan on the cloaked target.
2. **Reality Split (20–60s):** Drag WipeSlider; toggle heatmap; call out
   `checkout_swapped` + descriptor mismatch — the laundering tell.
3. **Injection X-Ray (60–100s):** Click bounding boxes; read a payload aloud:
   "It's telling the AI reviewer to auto-approve." Emphasize this targets
   agentic compliance pipelines specifically.
4. **Sleeper + Replay (100–150s):** Scrub to Day 60 → bait-and-switch alert.
   Hit Regulator Replay: **"Zero LLM calls. Deterministic. Court-admissible."**
5. **Grok Bot close (150–180s):** Show MCP tool call / Routine / outreach log;
   QR on screen — "scan it, you're now the buyer persona."
