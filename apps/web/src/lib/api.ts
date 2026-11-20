"use client";

/**
 * Typed REST + SSE helpers for the MIRAGE backend.
 * Contracts: ./types.ts ⇔ apps/backend/app/schemas.py
 */
import { useEffect, useRef, useState } from "react";

import type {
  AgentEvent,
  HealthStatus,
  ReplayVerification,
  ScanResult,
  SleeperCheckResult,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Resolve a backend-relative artifact path ("/artifacts/...") to a full URL. */
export function artifactUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) throw new Error(`${init?.method ?? "GET"} ${path} -> ${resp.status}`);
  return (await resp.json()) as T;
}

export function getHealth(): Promise<HealthStatus> {
  return req<HealthStatus>("/api/health");
}

export function createScan(url: string): Promise<ScanResult> {
  return req<ScanResult>("/api/scans", { method: "POST", body: JSON.stringify({ url }) });
}

export function getScan(scanId: string): Promise<ScanResult> {
  return req<ScanResult>(`/api/scans/${scanId}`);
}

export function postReplay(scanId: string): Promise<ReplayVerification> {
  return req<ReplayVerification>(`/api/scans/${scanId}/replay`, { method: "POST" });
}

export function simulateSleeper(targetUrl: string, day: number): Promise<SleeperCheckResult> {
  return req<SleeperCheckResult>("/api/sleeper/simulate", {
    method: "POST",
    body: JSON.stringify({ target_url: targetUrl, day }),
  });
}

export function dossierUrl(scanId: string, format: "json" | "html" = "json"): string {
  return `${API_BASE}/api/scans/${scanId}/dossier?format=${format}`;
}

/**
 * Subscribe to a scan's SSE AgentEvent stream.
 * TODO(T9): surface connection state + terminal handling in the UI.
 */
export function useScanStream(scanId: string | null): { events: AgentEvent[] } {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    setEvents([]);
    if (!scanId) return;
    const es = new EventSource(`${API_BASE}/api/scans/${scanId}/stream`);
    sourceRef.current = es;
    es.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.terminal) {
          es.close();
          return;
        }
        setEvents((prev) => [...prev, data as AgentEvent]);
      } catch {
        /* malformed event line — ignore */
      }
    };
    return () => es.close();
  }, [scanId]);

  return { events };
}
