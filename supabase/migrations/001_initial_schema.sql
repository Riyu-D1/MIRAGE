-- MIRAGE — initial schema (paste into Supabase SQL Editor at 10:30 AM)
-- Tables: scans, agent_events, evidence_artifacts, sleeper_monitors
-- + Realtime publication + hackathon-friendly RLS.

create extension if not exists "pgcrypto";

-- ── scans: one row per MIRAGE scan; full ScanResult contract lives in result ──
create table if not exists public.scans (
  id uuid primary key default gen_random_uuid(),
  target_url text not null,
  created_at timestamptz not null default now(),
  verdict text not null default 'PENDING',
  reality_gap_score integer not null default 0,
  evidence_merkle_hash text,
  result jsonb not null default '{}'::jsonb
);

-- ── agent_events: drives the MissionRail SSE feed + Supabase Realtime ─────────
create table if not exists public.agent_events (
  id uuid primary key default gen_random_uuid(),
  scan_id uuid references public.scans(id) on delete cascade,
  "timestamp" timestamptz not null default now(),
  step text not null,
  agent text not null,
  status text not null check (status in ('running','done','alert','error')),
  detail text not null default '',
  latency_ms double precision,
  payload jsonb not null default '{}'::jsonb
);
create index if not exists agent_events_scan_idx on public.agent_events (scan_id, "timestamp");

-- ── evidence_artifacts: immutable evidence vault (hashes only, bytes on disk) ──
create table if not exists public.evidence_artifacts (
  id uuid primary key default gen_random_uuid(),
  scan_id uuid references public.scans(id) on delete cascade,
  kind text not null,                 -- screenshot_png | page_html | heatmap_png | har | manifest
  path text not null,                 -- /artifacts/{scan_id}/...
  sha256 text not null,
  created_at timestamptz not null default now(),
  meta jsonb not null default '{}'::jsonb
);
create index if not exists evidence_artifacts_scan_idx on public.evidence_artifacts (scan_id);

-- ── sleeper_monitors: Day 1 -> 60 post-onboarding drift watch ─────────────────
create table if not exists public.sleeper_monitors (
  id uuid primary key default gen_random_uuid(),
  target_url text not null,
  baseline_hash text not null,
  baseline_gateway text,
  registered_at timestamptz not null default now(),
  last_checked_at timestamptz,
  last_hash text,
  alert_triggered boolean not null default false,
  history jsonb not null default '[]'::jsonb   -- SleeperCheckResult[]
);

-- ── Realtime: stream new rows to the Mission Control UI ───────────────────────
do $$
begin
  alter publication supabase_realtime add table public.agent_events;
exception when duplicate_object then null; when undefined_object then null;
end $$;
do $$
begin
  alter publication supabase_realtime add table public.sleeper_monitors;
exception when duplicate_object then null; when undefined_object then null;
end $$;
do $$
begin
  alter publication supabase_realtime add table public.scans;
exception when duplicate_object then null; when undefined_object then null;
end $$;

-- ── RLS (hackathon-friendly): anon/authenticated can read + write everything ──
-- service_role bypasses RLS entirely. Tighten before any real deployment.
alter table public.scans enable row level security;
alter table public.agent_events enable row level security;
alter table public.evidence_artifacts enable row level security;
alter table public.sleeper_monitors enable row level security;

create policy "scans anon all" on public.scans
  for all to anon, authenticated using (true) with check (true);
create policy "agent_events anon all" on public.agent_events
  for all to anon, authenticated using (true) with check (true);
create policy "evidence_artifacts anon all" on public.evidence_artifacts
  for all to anon, authenticated using (true) with check (true);
create policy "sleeper_monitors anon all" on public.sleeper_monitors
  for all to anon, authenticated using (true) with check (true);
