"use client";

/**
 * ThreeLensStage — the 3-column Reality Split: Lens A (compliance), Lens B
 * (buyer), Lens C (injection X-ray) + Reality-Gap gauge.
 * TODO(T8): compose WipeSlider + InjectionOverlay and animate the gauge:
 *   Lens A -> scan.persona_a screenshot
 *   Lens B -> scan.persona_b screenshot inside WipeSlider (with heatmap toggle)
 *   Lens C -> InjectionOverlay over persona_a screenshot + Reality-Gap radial
 *             gauge (0-100, crimson >=70) driven by scan.reality_gap_score
 */
import type { ScanResult } from "@/lib/types";

interface ThreeLensStageProps {
  scan: ScanResult | null;
}

const LENSES = [
  { id: "a", title: "LENS A · COMPLIANCE", accent: "text-accent-cyan" },
  { id: "b", title: "LENS B · BUYER", accent: "text-accent-violet" },
  { id: "c", title: "LENS C · INJECTION X-RAY", accent: "text-accent-crimson" },
];

export default function ThreeLensStage({ scan }: ThreeLensStageProps) {
  return (
    <section className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      {LENSES.map((lens) => (
        <div key={lens.id} className="rounded-lg border border-line bg-panel p-3">
          <h3 className={`mb-2 font-mono text-xs font-bold tracking-widest ${lens.accent}`}>
            {lens.title}
          </h3>
          <div className="flex aspect-[8/5] items-center justify-center rounded border border-line bg-obsidian font-mono text-xs text-ink-secondary">
            {scan ? "awaiting captures…" : "no scan"}
          </div>
        </div>
      ))}
      <div className="rounded-lg border border-line bg-panel p-3 lg:col-span-3">
        <span className="font-mono text-xs text-ink-secondary">
          REALITY-GAP:{" "}
        </span>
        <span className="font-mono text-sm font-bold text-accent-crimson">
          {scan ? `${scan.reality_gap_score}/100` : "—"}
        </span>
      </div>
    </section>
  );
}
