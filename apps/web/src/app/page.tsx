"use client";

/**
 * Mission Control — the MIRAGE demo console.
 * Live wiring: scan submit -> PENDING scan -> live SSE events -> terminal
 * refetch -> real captures in every panel.
 * TODO(T9): verdict-driven visual states + polish (see docs/TASKS.md).
 */
import { useEffect, useState } from "react";

import MissionRail from "@/components/MissionRail";
import PaymentRailFork from "@/components/PaymentRailFork";
import RegulatorReplayBar from "@/components/RegulatorReplayBar";
import SleeperTimeline from "@/components/SleeperTimeline";
import StageQrModal from "@/components/StageQrModal";
import ThreeLensStage from "@/components/ThreeLensStage";
import TopCommandBar from "@/components/TopCommandBar";
import WipeSlider from "@/components/WipeSlider";
import {
  createScan,
  getHealth,
  getScan,
  postReplay,
  simulateSleeper,
  useScanStream,
} from "@/lib/api";
import type {
  HealthStatus,
  ReplayVerification,
  ScanResult,
  SleeperCheckResult,
} from "@/lib/types";

export default function MissionControl() {
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [qrOpen, setQrOpen] = useState(false);
  const [replay, setReplay] = useState<ReplayVerification | null>(null);
  const [replaying, setReplaying] = useState(false);
  const [sleeper, setSleeper] = useState<SleeperCheckResult | null>(null);
  const { events } = useScanStream(scan?.scan_id ?? null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  // POST /api/scans returns PENDING immediately — when the SSE stream hits a
  // terminal pipeline step, refetch the completed ScanResult for the panels.
  useEffect(() => {
    const done = events.some(
      (e) => e.step === "pipeline.complete" || e.step === "pipeline.error",
    );
    if (done && scan?.verdict === "PENDING") {
      getScan(scan.scan_id).then(setScan).catch(() => undefined);
    }
  }, [events, scan]);

  const onScan = (url: string) => {
    setReplay(null);
    createScan(url).then(setScan).catch(() => setScan(null));
  };

  const onReplay = () => {
    if (!scan) return;
    setReplaying(true);
    postReplay(scan.scan_id)
      .then(setReplay)
      .finally(() => setReplaying(false));
  };

  const onSleeper = (day: number) => {
    simulateSleeper(scan?.target_url ?? "http://localhost:8001/", day).then(setSleeper);
  };

  return (
    <main className="flex min-h-screen flex-col">
      <TopCommandBar onScan={onScan} onOpenQr={() => setQrOpen(true)} health={health} />
      <div className="grid flex-1 grid-cols-1 gap-3 p-3 xl:grid-cols-[1fr_320px]">
        <div className="flex flex-col gap-3">
          <ThreeLensStage scan={scan} />
          <WipeSlider
            beforeUrl={scan?.persona_a?.screenshot_url ?? null}
            afterUrl={scan?.persona_b?.screenshot_url ?? null}
            heatmapUrl={scan?.divergence?.heatmap_url ?? null}
          />
          <PaymentRailFork divergence={scan?.divergence ?? null} />
          <SleeperTimeline onCheck={onSleeper} result={sleeper} />
          <RegulatorReplayBar
            scanId={scan?.scan_id ?? null}
            onReplay={onReplay}
            result={replay}
            running={replaying}
          />
        </div>
        <MissionRail events={events} osint={scan?.osint ?? null} />
      </div>
      <StageQrModal open={qrOpen} onClose={() => setQrOpen(false)} />
    </main>
  );
}
