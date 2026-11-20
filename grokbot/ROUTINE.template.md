# Grok Bot Routine — MIRAGE Sleeper Watch (paste into Grok Bot console)

```yaml
name: mirage-sleeper-watch
description: >
  Periodic post-onboarding drift check. Re-probes approved merchants and
  alerts when the surface diverges from its Day-1 approved baseline —
  catches the classic bait-and-switch.

schedule:
  # Demo-friendly cadence; tighten/loosen as needed for the routine syntax
  # Grok Bot exposes (cron or natural interval both fine).
  every: 30m

uses_skill: mirage-merchant-forensics

routine: |
  1. List active sleeper monitors:
       POST {BACKEND_URL}/api/sleeper/register has already stored baselines;
       (T5) fetch the monitor list from the backend or Supabase
       sleeper_monitors table.
  2. For each monitor, call mirage_sleeper_check(target_url, day=N) where N is
     the current simulated day (1, 30, 60 in the demo).
  3. If alert_triggered is true:
       a. POST {BACKEND_URL}/api/webhooks/grokbot with
          {"type": "sleeper_trigger", "target_url": ..., "day": N,
           "baseline_hash": ..., "current_hash": ...}
       b. Emit an alert event so MissionRail turns crimson live.
  4. Otherwise record last_checked_at and keep monitoring.

notes: |
  The demo fast-forwards days via the /sleeper?day=N endpoint on the
  target merchant — a Routine run maps one simulated day to one check.
```
