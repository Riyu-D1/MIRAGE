# MIRAGE × Grok Bot — 10:30 AM Activation Checklist (~5 min)

Do this the moment sponsor credits/keys arrive. Everything already works
offline; this flips the live switches.

## 1. Supabase (2 min)

- [ ] Create project → copy URL + anon + service_role keys
- [ ] Paste into `.env`: `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
      `SUPABASE_SERVICE_ROLE_KEY`, `NEXT_PUBLIC_SUPABASE_URL`,
      `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] SQL Editor → paste `supabase/migrations/001_initial_schema.sql` → Run
- [ ] Restart backend → `curl :8000/api/health` shows `"supabase": true`

## 2. Grok Bot (2 min)

- [ ] Create webhook endpoint → paste `GROKBOT_WEBHOOK_URL` + `GROKBOT_API_KEY`
      into `.env`, restart backend
- [ ] Create the Skill from `grokbot/SKILL.template.md` (points Grok Bot's MCP
      client at `http://<host>:8002` / `MCP_SERVER_URL`)
- [ ] Start the MCP server: `python apps/mcp-server/server.py` (or `scripts/dev`)
- [ ] Create the Routine from `grokbot/ROUTINE.template.md` (Sleeper Watch)

## 3. OSINT keys (1 min)

- [ ] `TAVILY_API_KEY=` and `COMPANIES_HOUSE_API_KEY=` into `.env`
- [ ] Restart backend → health pills flip green

## 4. Verify (30 s)

- [ ] `curl :8000/api/health` → all four integrations `true`
- [ ] Run one scan from Mission Control → watch `agent_events` rows appear in
      the Supabase table editor + live SSE in the UI
- [ ] `pytest tests/` still green
- [ ] In `docs/DEMO_CHECKLIST.md`, tick the 10:30 section
