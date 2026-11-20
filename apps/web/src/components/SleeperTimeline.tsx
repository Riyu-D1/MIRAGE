"use client";

/**
 * SleeperTimeline — Day 1 / 30 / 60 scrubber driving sleeper-watch checks.
 * TODO(T9): drag-scrub track, fracture animation on drift, hash comparison
 * readout (baseline vs current).
 */
import type { SleeperCheckResult } from "@/lib/types";

interface SleeperTimelineProps {
  onCheck: (day: number) => void;
  result: SleeperCheckResult | null;
}

const DAYS = [1, 30, 60];

export default function SleeperTimeline({ onCheck, result }: SleeperTimelineProps) {
  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <h3 className="mb-3 font-mono text-xs font-bold tracking-widest text-ink-secondary">
        SLEEPER WATCH · DAY 1 → 60
      </h3>
      <div className="flex items-center gap-2">
        {DAYS.map((d) => (
          <button
            key={d}
            onClick={() => onCheck(d)}
            className={`rounded border px-4 py-1.5 font-mono text-sm ${
              result?.day === d
                ? result.alert_triggered
                  ? "border-accent-crimson text-accent-crimson"
                  : "border-accent-green text-accent-green"
                : "border-line text-ink-secondary hover:text-ink-primary"
            }`}
          >
            DAY {d}
          </button>
        ))}
        {result && (
          <span
            className={`ml-3 font-mono text-xs ${
              result.alert_triggered ? "text-accent-crimson" : "text-accent-green"
            }`}
          >
            {result.alert_triggered ? "⚠ HASH FRACTURE — BAIT-AND-SWITCH" : "INTACT"}
          </span>
        )}
      </div>
    </div>
  );
}
