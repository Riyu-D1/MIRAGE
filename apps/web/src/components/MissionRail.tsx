"use client";

/**
 * MissionRail — live SSE Grok Bot mission stepper + OSINT & covert-outreach
 * cards. TODO(T9): status icons/animation, OSINT detail cards, auto-scroll.
 */
import type { AgentEvent, OsintSummary } from "@/lib/types";

interface MissionRailProps {
  events: AgentEvent[];
  osint: OsintSummary | null;
}

const STATUS_COLOR: Record<AgentEvent["status"], string> = {
  running: "text-accent-cyan",
  done: "text-accent-green",
  alert: "text-accent-crimson",
  error: "text-accent-amber",
};

export default function MissionRail({ events, osint }: MissionRailProps) {
  return (
    <aside className="flex h-full flex-col gap-3 rounded-lg border border-line bg-panel p-4">
      <h3 className="font-mono text-xs font-bold tracking-widest text-ink-secondary">
        MISSION FEED
      </h3>
      <div className="flex-1 space-y-1.5 overflow-y-auto">
        {events.length === 0 && (
          <p className="font-mono text-xs text-ink-secondary">awaiting scan…</p>
        )}
        {events.map((e) => (
          <div key={e.id} className="flex items-baseline gap-2 font-mono text-xs">
            <span className={STATUS_COLOR[e.status]}>●</span>
            <span className="text-ink-primary">{e.step}</span>
            <span className="truncate text-ink-secondary">{e.detail}</span>
            {e.latency_ms != null && (
              <span className="ml-auto text-accent-cyan">{e.latency_ms.toFixed(1)}ms</span>
            )}
          </div>
        ))}
      </div>
      {osint && (
        <div className="rounded border border-line bg-obsidian p-3 font-mono text-xs">
          <p className="text-ink-secondary">
            OSINT · {osint.source_mode === "live" ? "LIVE" : "CACHED"}
          </p>
          <p className="text-ink-primary">{osint.company_name ?? "—"}</p>
          {osint.covert_outreach_log && (
            <p className="mt-1 text-accent-violet">
              outreach: {osint.covert_outreach_log.status}
            </p>
          )}
        </div>
      )}
    </aside>
  );
}
