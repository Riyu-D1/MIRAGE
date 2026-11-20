"use client";

/**
 * RegulatorReplayBar — "Verify Deterministically (0 LLM Calls)" trigger +
 * result readout + evidence dossier export link.
 * TODO(T9): per-check expandable list, animated verification sweep.
 */
import { dossierUrl } from "@/lib/api";
import type { ReplayVerification } from "@/lib/types";

interface RegulatorReplayBarProps {
  scanId: string | null;
  onReplay: () => void;
  result: ReplayVerification | null;
  running: boolean;
}

export default function RegulatorReplayBar({
  scanId,
  onReplay,
  result,
  running,
}: RegulatorReplayBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-panel px-4 py-3">
      <button
        onClick={onReplay}
        disabled={!scanId || running}
        className="rounded border border-accent-green px-4 py-1.5 font-mono text-sm text-accent-green disabled:opacity-40"
      >
        {running ? "VERIFYING…" : "VERIFY DETERMINISTICALLY (0 LLM CALLS)"}
      </button>
      {result && (
        <>
          <span
            className={`font-mono text-sm font-bold ${
              result.verified && result.hash_integrity === "EXACT_MATCH"
                ? "text-accent-green"
                : "text-accent-crimson"
            }`}
          >
            {result.hash_integrity} · {result.llm_calls} LLM CALLS ·{" "}
            {result.elapsed_ms.toFixed(1)}ms
          </span>
          <span className="font-mono text-xs text-ink-secondary">
            {result.checks.filter((c) => c.passed).length}/{result.checks.length} checks passed
          </span>
        </>
      )}
      {scanId && (
        <a
          href={dossierUrl(scanId)}
          target="_blank"
          rel="noreferrer"
          className="ml-auto font-mono text-xs text-accent-cyan underline-offset-2 hover:underline"
        >
          EXPORT EVIDENCE DOSSIER ↗
        </a>
      )}
    </div>
  );
}
