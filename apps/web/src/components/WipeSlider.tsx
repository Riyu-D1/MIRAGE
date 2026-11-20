"use client";

/**
 * WipeSlider — draggable before/after X-Ray comparison over two 1280x800
 * persona screenshots with pixel-diff heatmap toggle.
 * TODO(T8): polish handle, labels, opacity blending, touch support.
 */
import { useRef, useState } from "react";

import { artifactUrl } from "@/lib/api";

interface WipeSliderProps {
  beforeUrl: string | null; // persona A screenshot (relative /artifacts path)
  afterUrl: string | null; // persona B screenshot
  heatmapUrl: string | null;
}

export default function WipeSlider({ beforeUrl, afterUrl, heatmapUrl }: WipeSliderProps) {
  const [pos, setPos] = useState(50);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const before = artifactUrl(beforeUrl);
  const after = artifactUrl(afterUrl);
  const heatmap = artifactUrl(heatmapUrl);

  const update = (clientX: number) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    setPos(Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100)));
  };

  return (
    <div className="relative">
      <div
        ref={ref}
        className="relative aspect-[8/5] w-full touch-none select-none overflow-hidden rounded border border-line bg-obsidian"
        onPointerDown={(e) => {
          (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
          update(e.clientX);
        }}
        onPointerMove={(e) => e.buttons === 1 && update(e.clientX)}
      >
        {after && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={after} alt="buyer persona" className="absolute inset-0 h-full w-full object-cover" />
        )}
        {before && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={before}
            alt="compliance persona"
            className="absolute inset-0 h-full w-full object-cover"
            style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}
          />
        )}
        {showHeatmap && heatmap && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={heatmap} alt="pixel diff heatmap" className="absolute inset-0 h-full w-full object-cover opacity-70" />
        )}
        {!before && !after && (
          <div className="absolute inset-0 flex items-center justify-center font-mono text-xs text-ink-secondary">
            no captures yet
          </div>
        )}
        <div
          className="absolute inset-y-0 w-0.5 bg-ink-primary"
          style={{ left: `${pos}%` }}
        >
          <div className="absolute top-1/2 h-9 w-9 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-ink-primary bg-obsidian/80" />
        </div>
      </div>
      <button
        onClick={() => setShowHeatmap((v) => !v)}
        className={`absolute right-2 top-2 rounded border px-2 py-0.5 font-mono text-[11px] ${
          showHeatmap
            ? "border-accent-heat text-accent-heat"
            : "border-line text-ink-secondary"
        }`}
      >
        HEATMAP
      </button>
    </div>
  );
}
