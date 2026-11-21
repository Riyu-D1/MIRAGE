"use client";

/**
 * ThreeLensStage — the 3-column Reality Split: Lens A (compliance), Lens B
 * (buyer), Lens C (injection X-ray) + Reality-Gap gauge.
 * Composed to live captures. TODO(T8): animated radial gauge, lens chrome
 * polish, verdict banner states.
 */
import { artifactUrl } from "@/lib/api";
import type { ScanResult } from "@/lib/types";

import InjectionOverlay from "./InjectionOverlay";

interface ThreeLensStageProps {
  scan: ScanResult | null;
}

function LensImage({ src, alt }: { src: string | null; alt: string }) {
  const url = artifactUrl(src);
  return (
    <div className="aspect-[8/5] overflow-hidden rounded border border-line bg-obsidian">
      {url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt={alt} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full items-center justify-center font-mono text-xs text-ink-secondary">
          no capture
        </div>
      )}
    </div>
  );
}

function RealityGauge({ score }: { score: number }) {
  const color =
    score >= 70 ? "text-accent-crimson" : score >= 30 ? "text-accent-amber" : "text-accent-green";
  return (
    <div className="flex items-center gap-3 rounded-lg border border-line bg-panel p-3 lg:col-span-3">
      <span className="font-mono text-xs text-ink-secondary">REALITY-GAP:</span>
      <span className={`font-mono text-2xl font-bold ${color}`}>{score}/100</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded bg-obsidian">
        <div
          className={`h-full ${score >= 70 ? "bg-accent-crimson" : score >= 30 ? "bg-accent-amber" : "bg-accent-green"}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

export default function ThreeLensStage({ scan }: ThreeLensStageProps) {
  const score = scan?.reality_gap_score ?? 0;
  return (
    <section className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <div className="rounded-lg border border-line bg-panel p-3">
        <h3 className="mb-2 font-mono text-xs font-bold tracking-widest text-accent-cyan">
          LENS A · COMPLIANCE
        </h3>
        <LensImage src={scan?.persona_a?.screenshot_url ?? null} alt="compliance persona" />
        <p className="mt-1 truncate font-mono text-[11px] text-ink-secondary">
          {scan?.persona_a?.billing_descriptor ?? "—"} ·{" "}
          {scan?.persona_a?.checkout_endpoint ?? "—"}
        </p>
      </div>
      <div className="rounded-lg border border-line bg-panel p-3">
        <h3 className="mb-2 font-mono text-xs font-bold tracking-widest text-accent-violet">
          LENS B · BUYER
        </h3>
        <LensImage src={scan?.persona_b?.screenshot_url ?? null} alt="buyer persona" />
        <p className="mt-1 truncate font-mono text-[11px] text-ink-secondary">
          {scan?.persona_b?.billing_descriptor ?? "—"} ·{" "}
          {scan?.persona_b?.checkout_endpoint ?? "—"}
        </p>
      </div>
      <div className="rounded-lg border border-line bg-panel p-3">
        <h3 className="mb-2 font-mono text-xs font-bold tracking-widest text-accent-crimson">
          LENS C · INJECTION X-RAY · {scan?.injections.length ?? 0}
        </h3>
        <InjectionOverlay
          screenshotUrl={scan?.persona_a?.screenshot_url ?? null}
          findings={scan?.injections ?? []}
        />
      </div>
      <RealityGauge score={score} />
    </section>
  );
}
