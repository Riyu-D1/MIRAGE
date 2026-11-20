"use client";

/**
 * Mission Control — the MIRAGE demo console.
 * Shell wiring: scan submit -> SSE events -> stub panels.
 * TODO(T9): full live pipeline wiring + verdict-driven visual states.
 */
import { useEffect, useState } from "react";

import MissionRail from "@/components/MissionRail";
import PaymentRailFork from "@/components/PaymentRailFork";
import RegulatorReplayBar from "@/components/RegulatorReplayBar";
import SleeperTimeline from "@/components/SleeperTimeline";
import StageQrModal from "@/components/StageQrModal";
import ThreeLensStage from "@/components/ThreeLensStage";
import TopCommandBar from "@/components/TopCommandBar";
import {
  createScan,
  getHealth,
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
