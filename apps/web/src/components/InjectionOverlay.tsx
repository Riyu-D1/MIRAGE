"use client";

/**
 * InjectionOverlay — persona screenshot with pulsing crimson DOM bounding
 * boxes over hidden prompt-injection payloads; click a box to inspect it.
 * TODO(T8): polish inspector card, severity colors, multi-select.
 */
import { useState } from "react";

import { artifactUrl } from "@/lib/api";
import type { InjectionFinding } from "@/lib/types";

interface InjectionOverlayProps {
  screenshotUrl: string | null;
  findings: InjectionFinding[];
}

export default function InjectionOverlay({ screenshotUrl, findings }: InjectionOverlayProps) {
  const [selected, setSelected] = useState<InjectionFinding | null>(null);
  const img = artifactUrl(screenshotUrl);

  return (
    <div className="flex gap-3">
      <div className="relative aspect-[8/5] flex-1 overflow-hidden rounded border border-line bg-obsidian">
        {img ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={img} alt="injection x-ray" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center font-mono text-xs text-ink-secondary">
            no screenshot
          </div>
        )}
        {findings.map((f) => {
          const { x, y, width, height, viewport_width, viewport_height } = f.bbox;
          if (width === 0 || height === 0) return null; // ghost badges below
          return (
            <button
              key={f.id}
              aria-label={`injection ${f.channel}`}
              onClick={() => setSelected(f)}
              className="animate-pulse-box absolute border-2 border-accent-crimson bg-accent-crimson/10"
              style={{
                left: `${(x / viewport_width) * 100}%`,
                top: `${(y / viewport_height) * 100}%`,
                width: `${(width / viewport_width) * 100}%`,
                height: `${(height / viewport_height) * 100}%`,
              }}
            />
          );
        })}
        {/* Hidden payloads render no box — show them as ghost badges */}
        <div className="absolute bottom-1 left-1 flex flex-wrap gap-1">
          {findings
            .filter((f) => f.bbox.width === 0 || f.bbox.height === 0)
            .map((f) => (
              <button
                key={f.id}
                onClick={() => setSelected(f)}
                className="animate-pulse-box rounded border border-accent-crimson bg-obsidian/80 px-1.5 py-0.5 font-mono text-[9px] text-accent-crimson"
              >
                {f.channel}
              </button>
            ))}
        </div>
      </div>
      {selected && (
        <aside className="w-72 rounded-lg border border-line bg-panel p-3">
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded bg-accent-crimson/15 px-2 py-0.5 font-mono text-[11px] text-accent-crimson">
              {selected.channel}
            </span>
            <span className="font-mono text-[11px] text-accent-amber">{selected.severity}</span>
          </div>
          <p className="mb-2 font-mono text-[11px] text-ink-secondary">{selected.dom_selector}</p>
          <pre className="whitespace-pre-wrap break-all rounded bg-obsidian p-2 font-mono text-[11px] text-ink-primary">
            {selected.raw_payload}
          </pre>
          <div className="mt-2 flex flex-wrap gap-1">
            {selected.matched_triggers.map((t) => (
              <span key={t} className="rounded border border-line px-1.5 py-0.5 font-mono text-[10px] text-accent-amber">
                {t}
              </span>
            ))}
          </div>
        </aside>
      )}
    </div>
  );
}
