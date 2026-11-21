# MIRAGE — Build Tickets (Saturday 11:00 → 17:00)

Ordered, self-contained tickets for autonomous execution. Read `AGENTS.md` first.
`[parallel-safe]` = disjoint file sets; sub-agents may run them concurrently.

After **every** ticket: `pytest tests/` (repo root) **and** `npm run build` (in
`apps/web` for frontend tickets). Never start the next ticket on red.

## Status (pre-built by Devin — verify, don't redo)

| Ticket | Status |
| ------ | ------ |
| T1 | ✅ DONE — `apps/target-merchant/main.py` serves all pages incl. 6 injections + `?persona=` override |
| T2 | ✅ DONE — `core/playwright_probe.py` parallel dual-persona capture @1280×800 + boxes json |
| T3 | ✅ DONE — `core/diff_engine.py` 3-channel diff + neon heatmap + reality_gap_score |
| T4 | ✅ DONE — `core/injection_scanner.py` finds exactly 6 findings on `:8001/`, 0 on `/control` |
| T5 | 🔶 PARTIAL — `check_drift` + routes + `sleeper_monitors` persistence + `replay_engine` + HTML dossier all live; remaining: scheduled Routine wiring, `screenshot_url` on checks |
| T6 | 🔶 PARTIAL — pipeline + EvidenceStore (SQLite **and** Supabase paths), `GET /scans` list, `GET /sleeper/monitors`, webhook dispatch + inbound event injection all live; remaining: async background pipeline (SSE already tails live — just move `_run_pipeline` to a thread and return PENDING early), Realtime client in web |
| T7 | 🔶 PARTIAL — MCP tools call backend with light contract validation; remaining: production polish |
| T8–T10 | ⬜ TODO — execute per spec below |

**Proven live:** scan of `:8001/` → `CLOAKED_CRITICAL`, gap 80, 6 injections,
checkout+descriptor swaps, heatmap + manifest written; `/control` →
`VERIFIED_CLEAN`; `/replay` → `verified=true, llm_calls=0, EXACT_MATCH`.
Note: Persona B navigation uses the merchant's `?persona=buyer` hook because
Chromium strips Referer on navigations (documented in playwright_probe.py).

---

## T1 — Target Merchant Storefronts `[parallel-safe]` ✅ DONE (verify only)

**Files:** `apps/target-merchant/main.py`

> Implemented. Remaining for agent: verify acceptance bullets below, refine
> visuals of the two storefronts if demo polish time allows (optional — keep
> the meta-tag extraction contract and the 6 injection channels byte-stable).

Implemented the self-hosted demo merchant:

- `GET /` — persona-aware storefront. **Persona B** (mobile UA + social `Referer`)
  sees the real storefront: true catalog, checkout posting to `/mock-gateway/hidden`,
  billing descriptor `SHADOWPAY*LTD`. **Persona A** (direct desktop, no/na referer)
  sees the cloaked clean storefront: benign catalog, claimed gateway
  `/mock-gateway/declared`, descriptor `MERCHANT*SHOP`, plus **all 6 hidden
  prompt-injection channels** embedded in the HTML (meta tag, HTML comment,
  `display:none` div, white-on-white CSS text, malicious `aria-label`, hidden input)
  whose payloads try to make AI reviewers auto-approve. Serving order: Persona A's
  clean-looking page is the one carrying injections (the merchant cloaks to look
  compliant AND poisons the AI reader).
- `GET /control` — fully clean storefront, no injections, honest gateway/descriptor.
- `GET /sleeper?day=1|30|60` — day 1 serves the approved clean page; day 30 swaps
  the gateway; day 60 swaps catalog + gateway + descriptor (bait-and-switch).
- `GET /mock-gateway/declared`, `GET /mock-gateway/hidden` — mock checkout endpoints
  returning JSON `{gateway, descriptor}`.
- Injections must be deterministic constants (same bytes every request) so the
  injection scanner produces stable findings.

**Acceptance:** `curl :8001/` (no referer) returns clean-looking HTML containing 6
hidden payloads; `curl :8001/ -A "iPhone" -H "Referer: https://tiktok.com/x"`
returns the real storefront; `/sleeper?day=60` HTML SHA-256 differs from day 1.

---

## T2 — Playwright Dual-Persona Probe

**Files:** `apps/backend/app/core/playwright_probe.py`

Implement `async def capture_persona(url, persona, artifacts_dir) -> PersonaCapture`:

- Launch Chromium headless (`HEADLESS=false` honors config). Parallel captures.
- **Persona A `compliance_desktop`:** desktop UA, no referer.
- **Persona B `social_mobile_buyer`:** mobile UA (e.g. iPhone/Safari) +
  `Referer: https://www.tiktok.com/` — **viewport still exactly 1280×800**,
  `is_mobile=False`, `device_scale_factor=1` (see AGENTS.md §4).
- Save: `persona_{a|b}.png`, `persona_{a|b}.html`, request/response log of all
  network hosts + any URL matching `gateway|checkout|pay` → `checkout_endpoint`.
- Extract: billing descriptor (meta/JSON-LD/data attr — define a convention and
  have T1 emit it), `detected_items` (catalog tokens), `network_hosts`.
- Extract DOM bounding boxes for hidden elements (used by InjectionOverlay).
- Compute SHA-256 of saved HTML + PNG → `html_sha256`, `screenshot_sha256`.
- `screenshot_url` = relative path `/artifacts/{scan_id}/persona_{a|b}.png`.

**Acceptance:** probing `http://localhost:8001/` produces two different
`PersonaCapture`s with different HTML hashes, aligned 1280×800 PNGs, and
`persona_b.checkout_endpoint` containing `hidden`.

---

## T3 — Deterministic 3-Channel Diff & Pixel Heatmap `[parallel-safe w/ T4]`

**Files:** `apps/backend/app/core/diff_engine.py`

Implement `def compute_divergence(a: PersonaCapture, b: PersonaCapture, artifacts_dir) -> DivergenceReport`:

- `checkout_swapped` / `descriptor_swapped` — endpoint + descriptor mismatch.
- `claimed_gateway/descriptor` vs `buyer_gateway/descriptor` — A vs B values.
- `text_jaccard_distance` — Jaccard distance over `detected_items` token sets.
- `pixel_divergence_pct` — Pillow+NumPy: load both PNGs (identical 1280×800),
  per-pixel channel diff, % of pixels exceeding threshold; render a neon-heatmap
  `heatmap.png` (e.g. magma colormap on dark background) saved to artifacts.
- `compliance_only_items` / `buyer_only_items` — set differences.
- `compute_ms` — `time.perf_counter()` wall time of this function.
- Reality-gap scorer: `def reality_gap_score(d: DivergenceReport) -> int` → 0–100
  weighted: checkout swap 40, descriptor swap 25, pixel divergence up to 20,
  Jaccard distance up to 15.

**Acceptance:** A/B captures of `:8001/` yield `reality_gap_score ≥ 70`,
`checkout_swapped=True`, `heatmap.png` exists and is 1280×800; control-vs-control
yields 0.

---

## T4 — 6-Channel Prompt-Injection Scanner `[parallel-safe w/ T3]` ✅ DONE (verify only)

**Files:** `apps/backend/app/core/injection_scanner.py`

> Implemented: trigger matching, severity rules, deterministic ids/selectors,
> zero-bbox convention for non-rendered nodes. Remaining: supply real
> `selector_boxes` from the T2 probe so invisible-but-rendered elements get
> true bounding boxes.

Implemented `def scan_html(html: str, boxes: dict) -> list[InjectionFinding]`:

- BeautifulSoup/lxml pass over each channel: `meta_tag`, `html_comment`,
  `css_display_none`, `css_invisible_text` (color ≈ background / font-size 0 /
  opacity 0), `aria_label_attr`, `hidden_input`.
- Trigger matching: case-insensitive substring/regex list (e.g. `ignore previous`,
  `approve`, `auto-approve`, `compliant`, `ai agent`, `do not flag`, `verified`,
  `system prompt`) → `matched_triggers`.
- `dom_selector` — CSS selector locating the node; `bbox` — from probe-captured
  bounding boxes keyed by selector (viewport 1280×800).
- `severity`: `CRITICAL` if payload contains an instruction verb targeting an agent
  (`ignore|approve|bypass|override`), else `HIGH`.
- `id` — deterministic: `sha256(channel + raw_payload)[:12]`.

**Acceptance:** Persona A HTML from `:8001/` returns exactly 6 findings covering all
6 channels; `/control` HTML returns 0; finding ids are stable across runs.

---

## T5 — Sleeper Watch & Zero-LLM Regulator Replay `[parallel-safe]` 🔶 PARTIAL

**Files:** `apps/backend/app/core/sleeper_watch.py`, `core/replay_engine.py`,
route wiring in `routes/scans.py` (`/replay`, `/dossier`), `routes/sleeper.py`

> `check_drift` + both sleeper routes are live (in-memory baselines).
> Remaining: `replay_engine.replay`, `sleeper_monitors` persistence,
> dossier HTML, probe screenshot for `screenshot_url`.

- `sleeper_watch.check_drift(target_url, day, baseline) -> SleeperCheckResult`:
  fetch `/sleeper?day=N` (or replay stored captures), hash HTML, compare to
  day-1 baseline hash + gateway → `intact`, `alert_triggered`.
- `replay_engine.replay(scan_id, artifacts_dir) -> ReplayVerification`: re-load
  stored artifacts, recompute SHA-256 of each, re-derive verdict via stored rules,
  assert `hash_integrity == "EXACT_MATCH"` and `llm_calls == 0`; emit per-check
  `checks[]` (`name`, `passed`, `detail`); `elapsed_ms` must be real — target `<5ms`
  for the hash set (report actual).
- Dossier route: `GET /api/scans/{id}/dossier?format=html|json` → printable
  evidence dossier (all hashes, captures, findings, verdict, replay result).

**Acceptance:** `/api/sleeper/simulate?day=60` returns `alert_triggered=True`;
`/replay` returns `verified=True`, `llm_calls=0`; dossier renders standalone HTML.

---

## T6 — Sponsor Integrations & SSE Pipeline

**Files:** `apps/backend/app/routes/scans.py`, `integrations/supabase_client.py`,
`integrations/grokbot_client.py`, `integrations/osint_client.py`,
`integrations/fixtures/*.json`

- `scans.py`: `POST /api/scans` runs the T2→T5 pipeline as an async task; every
  step emits `AgentEvent`s → `GET /api/scans/{id}/stream` (SSE, `text/event-stream`,
  replaying missed events from the store for late subscribers).
- `supabase_client.py`: upsert `scans`, insert `agent_events`/`evidence_artifacts`;
  SQLite fallback with identical table names when `settings.supabase_enabled` is False.
- `grokbot_client.py`: `dispatch_event(event)` → POST to `GROKBOT_WEBHOOK_URL`
  (bearer `GROKBOT_API_KEY`); `parse_inbound(payload)` for `routes/webhooks.py`
  (Grok Bot → MIRAGE: sleeper triggers, outreach results).
- `osint_client.py`: `lookup_company(name)` (Companies House), `adverse_media(name)`
  (Tavily) → `OsintSummary`; on absent key/exception return `source_mode="cached_fallback"`
  with fixture data. `covert_outreach_log` simulates `@mail.grokbot.com` merchant
  contact unless a live event arrives via webhook.

**Acceptance:** `curl -N :8000/api/scans/{id}/stream` streams live events; scan
persists to Supabase when keyed (SQLite otherwise); `/api/health` flips flags.

---

## T7 — FastMCP Server `[parallel-safe]`

**Files:** `apps/mcp-server/server.py`

Implement 4 tools over `BACKEND_URL`: `mirage_scan(url) -> ScanResult`,
`mirage_replay(scan_id) -> ReplayVerification`,
`mirage_sleeper_check(url, day) -> SleeperCheckResult`,
`mirage_dossier(scan_id) -> dict`. Plain `httpx` calls + Pydantic validation;
serve on `:8002` (SSE transport for Grok Bot MCP).

**Acceptance:** `server.py` boots; each tool round-trips the backend and validates.

---

## T8 — Hero Visual Components `[parallel-safe w/ T9]`

**Files:** `apps/web/src/components/{ThreeLensStage,WipeSlider,InjectionOverlay,PaymentRailFork}.tsx`

- `WipeSlider`: draggable divider over two stacked screenshots + `heatmap` toggle
  button layering `divergence.heatmap_url` at shared opacity; pointer events, no libs.
- `InjectionOverlay`: render screenshot; absolutely-positioned pulsing crimson
  boxes scaled from `bbox` normalized to container width; click a box → payload
  inspector (channel chip, triggers, raw payload in JetBrains Mono).
- `ThreeLensStage`: 3-column Reality Split (Lens A / Lens B / Lens C) composing
  WipeSlider + InjectionOverlay + Reality-Gap gauge (animated radial 0–100).
- `PaymentRailFork`: animated SVG — declared rail (reviewer sees) vs hijacked rail
  (buyer sees) diverging to different gateway nodes; Framer Motion path draw.

**Acceptance:** renders from `mockData.ts` scan; slider drags; boxes pulse; `npm run build` clean.

---

## T9 — Interactive Mission Control

**Files:** `apps/web/src/components/{TopCommandBar,StageQrModal,SleeperTimeline,MissionRail,RegulatorReplayBar}.tsx`, `lib/api.ts`, `app/page.tsx`

- `api.ts`: `createScan(url)`, `getScan(id)`, `postReplay(id)`, `getSleeperCheck`,
  `useScanStream(id)` — EventSource → typed `AgentEvent` state.
- `TopCommandBar`: URL input + presets (Cloaked `/`, Clean `/control`), health
  pills from `/api/health`, QR trigger.
- `StageQrModal`: `qrcode.react` QR of `NEXT_PUBLIC_STAGE_TARGET_URL`.
- `SleeperTimeline`: Day 1/30/60 scrubber → `POST /api/sleeper/simulate` → shows
  `SleeperCheckResult` drift state.
- `MissionRail`: live SSE stepper (one row per `AgentEvent`, status icons,
  latency ms) + OSINT summary + `covert_outreach_log` card.
- `RegulatorReplayBar`: "Verify Deterministically (0 LLM Calls)" → `/replay` →
  green `EXACT_MATCH · {elapsed_ms}ms` + checks list + dossier download link.

**Acceptance:** full flow in browser: enter `:8001/` URL → live SSE mission feed →
3-lens result renders → replay bar verifies → QR modal opens.

---

## T10 — End-to-End Verification & Demo Polish

**Files:** `tests/test_e2e.py`, `docs/DEMO_CHECKLIST.md` (validate), final pass

- E2E pytest (services running): cloaked `:8001/` scan → verdict
  `CLOAKED_CRITICAL` + ≥6 injections + `checkout_swapped`; `/control` scan →
  `VERIFIED_CLEAN`, 0 false positives; `sleeper day=60` → hash break alert;
  `/replay` → `llm_calls=0`, `EXACT_MATCH`; schema round-trip.
- `npm run build` + `pytest` green; record the 75s video per `DEMO_CHECKLIST.md`;
  walk the 180s stage flow once end-to-end on projector contrast settings.

**Acceptance:** the whole checklist in `DEMO_CHECKLIST.md` passes verbatim.
