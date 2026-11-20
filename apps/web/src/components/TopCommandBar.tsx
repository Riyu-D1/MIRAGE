"use client";

/**
 * TopCommandBar — URL input, preset target buttons, live health pills,
 * Stage QR modal trigger. TODO(T9): wire health polling + scan submit state.
 */
import { useState } from "react";

import type { HealthStatus } from "@/lib/types";

interface TopCommandBarProps {
  onScan: (url: string) => void;
  onOpenQr: () => void;
  health: HealthStatus | null;
}

const PRESETS = [
  { label: "CLOAKED TARGET", url: "http://localhost:8001/" },
  { label: "CLEAN CONTROL", url: "http://localhost:8001/control" },
];

export default function TopCommandBar({ onScan, onOpenQr, health }: TopCommandBarProps) {
  const [url, setUrl] = useState(PRESETS[0].url);

  const pills = health
    ? Object.entries(health.integrations).map(([name, on]) => ({
        name: name.toUpperCase(),
        on,
      }))
    : [];

  return (
    <header className="flex flex-wrap items-center gap-3 border-b border-line bg-panel px-4 py-3">
      <span className="font-mono text-lg font-bold tracking-widest text-accent-cyan">
        MIRAGE
      </span>
      <input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="merchant URL"
        className="min-w-64 flex-1 rounded border border-line bg-obsidian px-3 py-1.5 font-mono text-sm text-ink-primary outline-none focus:border-accent-cyan"
      />
      <button
        onClick={() => onScan(url)}
        className="rounded bg-accent-cyan px-4 py-1.5 font-mono text-sm font-bold text-obsidian hover:opacity-90"
      >
        SCAN
      </button>
      {PRESETS.map((p) => (
        <button
          key={p.url}
          onClick={() => setUrl(p.url)}
          className="rounded border border-line px-3 py-1.5 font-mono text-xs text-ink-secondary hover:border-accent-violet hover:text-ink-primary"
        >
          {p.label}
        </button>
      ))}
      <button
        onClick={onOpenQr}
        className="rounded border border-line px-3 py-1.5 font-mono text-xs text-ink-secondary hover:border-accent-cyan hover:text-ink-primary"
      >
        STAGE QR
      </button>
      <div className="flex gap-2">
        {pills.length === 0 && (
          <span className="font-mono text-xs text-ink-secondary">health: —</span>
        )}
        {pills.map((p) => (
          <span
            key={p.name}
            className={`rounded-full border px-2 py-0.5 font-mono text-[11px] ${
              p.on
                ? "border-accent-green text-accent-green"
                : "border-line text-ink-secondary"
            }`}
          >
            {p.name} {p.on ? "●" : "○"}
          </span>
        ))}
      </div>
    </header>
  );
}
