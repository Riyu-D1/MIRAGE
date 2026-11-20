# Grok Bot Skill — MIRAGE Merchant Forensics (paste into Grok Bot console)

```yaml
name: mirage-merchant-forensics
description: >
  Investigate e-commerce merchants for transaction laundering using MIRAGE's
  deterministic tools: dual-persona cloaking scans, hidden prompt-injection
  X-ray, sleeper drift checks, and zero-LLM regulator replay. ALWAYS prefer
  these tools over freeform browsing — every tool output is evidence-grade
  (SHA-256 hashed, latency-timed).

mcp_servers:
  mirage:
    url: http://localhost:8002/sse   # set to MIRAGE MCP server (MCP_SERVER_URL)
    transport: sse

tools:
  - mirage_scan(url)              # -> ScanResult: verdict, reality_gap_score,
                                 #    persona captures, injections, divergence
  - mirage_replay(scan_id)        # -> ReplayVerification: 0-LLM re-check,
                                 #    EXACT_MATCH | MISMATCH
  - mirage_sleeper_check(url,day) # -> SleeperCheckResult: Day-N drift vs baseline
  - mirage_dossier(scan_id)       # -> printable evidence dossier

instructions: |
  1. Given a merchant URL, call mirage_scan and report the verdict.
  2. If verdict is CLOAKED_CRITICAL or INJECTION_DETECTED, call mirage_replay
     to confirm deterministically and cite the evidence hashes.
  3. For approved merchants, schedule mirage_sleeper_check at increasing days
     to catch bait-and-switch swaps.
  4. Write a short covert outreach email (from @mail.grokbot.com) when asked to
     verify merchant responsiveness; POST results back to
     {BACKEND_URL}/api/webhooks/grokbot as {"type": "outreach_result", ...}.
  5. Never assert laundering without a replay-verified artifact trail.
```
