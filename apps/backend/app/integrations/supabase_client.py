"""Supabase evidence store (T6).

Supabase Postgres when settings.supabase_enabled, else a local SQLite
fallback at artifacts/mirage.db with identical table names so the rest of
the codebase never branches. See supabase/migrations/001_initial_schema.sql.

Row shapes match the migration: the full ScanResult lives in scans.result,
the full AgentEvent in agent_events.payload — indexed columns are copies
for filtering.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import settings
from ..schemas import AgentEvent, ScanResult, SleeperCheckResult

_SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS scans (
  id TEXT PRIMARY KEY,
  target_url TEXT NOT NULL,
  created_at TEXT NOT NULL,
  verdict TEXT NOT NULL DEFAULT 'PENDING',
  reality_gap_score INTEGER NOT NULL DEFAULT 0,
  evidence_merkle_hash TEXT,
  result TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS agent_events (
  id TEXT PRIMARY KEY,
  scan_id TEXT,
  "timestamp" TEXT NOT NULL,
  step TEXT NOT NULL,
  agent TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  latency_ms REAL,
  payload TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS evidence_artifacts (
  id TEXT PRIMARY KEY,
  scan_id TEXT,
  kind TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  meta TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS sleeper_monitors (
  id TEXT PRIMARY KEY,
  target_url TEXT NOT NULL,
  baseline_hash TEXT NOT NULL,
  baseline_gateway TEXT,
  registered_at TEXT NOT NULL,
  last_checked_at TEXT,
  last_hash TEXT,
  alert_triggered INTEGER NOT NULL DEFAULT 0,
  history TEXT NOT NULL DEFAULT '[]'
);
"""


class EvidenceStore:
    """Persistence for scans, agent events, evidence, and sleeper monitors.

    Uses Supabase when keyed; SQLite otherwise. All methods are safe no-ops
    on failure — persistence must never break a scan.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.enabled: bool = settings.supabase_enabled
        self.db_path = db_path or settings.sqlite_path
        self._sb = None
        if self.enabled:
            try:
                from supabase import create_client

                self._sb = create_client(
                    settings.supabase_url, settings.supabase_service_role_key
                )
            except Exception:
                # Mis-keyed Supabase must not kill the backend — fall back
                # to SQLite so the demo still works offline.
                self.enabled = False
                self._sb = None
        if not self.enabled:
            with self._sqlite() as con:
                con.executescript(_SQLITE_DDL)

    def _sqlite(self) -> sqlite3.Connection:
        """Connection to the SQLite fallback DB (creates parent dir)."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    # ── scans ────────────────────────────────────────────────────────────

    def upsert_scan(self, scan: ScanResult) -> None:
        """Upsert a scan row (full ScanResult stored in `result`)."""
        try:
            if self.enabled:
                self._sb.table("scans").upsert(
                    {
                        "id": scan.scan_id,
                        "target_url": scan.target_url,
                        "created_at": scan.created_at,
                        "verdict": scan.verdict.value,
                        "reality_gap_score": scan.reality_gap_score,
                        "evidence_merkle_hash": scan.evidence_merkle_hash,
                        "result": scan.model_dump(mode="json"),
                    }
                ).execute()
                return
            with self._sqlite() as con:
                con.execute(
                    "INSERT OR REPLACE INTO scans (id, target_url, created_at, verdict,"
                    " reality_gap_score, evidence_merkle_hash, result) VALUES (?,?,?,?,?,?,?)",
                    (
                        scan.scan_id,
                        scan.target_url,
                        scan.created_at,
                        scan.verdict.value,
                        scan.reality_gap_score,
                        scan.evidence_merkle_hash,
                        scan.model_dump_json(),
                    ),
                )
        except Exception:
            pass

    def get_scan(self, scan_id: str) -> ScanResult | None:
        """Load a scan row and hydrate ScanResult from `result`."""
        try:
            if self.enabled:
                rows = (
                    self._sb.table("scans")
                    .select("result")
                    .eq("id", scan_id)
                    .limit(1)
                    .execute()
                    .data
                )
                return ScanResult.model_validate(rows[0]["result"]) if rows else None
            with self._sqlite() as con:
                row = con.execute(
                    "SELECT result FROM scans WHERE id = ?", (scan_id,)
                ).fetchone()
            return ScanResult.model_validate_json(row[0]) if row else None
        except Exception:
            return None

    def list_scans(self, limit: int = 50) -> list[ScanResult]:
        """Recent scans, newest first — powers a scan-history view."""
        try:
            if self.enabled:
                rows = (
                    self._sb.table("scans")
                    .select("result")
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                    .data
                )
                return [ScanResult.model_validate(r["result"]) for r in rows]
            with self._sqlite() as con:
                rows = con.execute(
                    "SELECT result FROM scans ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [ScanResult.model_validate_json(r[0]) for r in rows]
        except Exception:
            return []

    # ── agent_events ─────────────────────────────────────────────────────

    def insert_event(self, event: AgentEvent) -> None:
        """Insert an AgentEvent (drives SSE replay + Realtime when keyed)."""
        try:
            if self.enabled:
                self._sb.table("agent_events").insert(
                    {
                        "id": event.id,
                        "scan_id": event.scan_id,
                        "timestamp": event.timestamp,
                        "step": event.step,
                        "agent": event.agent,
                        "status": event.status,
                        "detail": event.detail,
                        "latency_ms": event.latency_ms,
                        "payload": event.model_dump(mode="json"),
                    }
                ).execute()
                return
            with self._sqlite() as con:
                con.execute(
                    "INSERT OR REPLACE INTO agent_events"
                    " (id, scan_id, \"timestamp\", step, agent, status, detail,"
                    "  latency_ms, payload) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        event.id,
                        event.scan_id,
                        event.timestamp,
                        event.step,
                        event.agent,
                        event.status,
                        event.detail,
                        event.latency_ms,
                        event.model_dump_json(),
                    ),
                )
        except Exception:
            pass

    def list_events(self, scan_id: str) -> list[AgentEvent]:
        """Ordered events for a scan (SSE replay for late subscribers)."""
        try:
            if self.enabled:
                rows = (
                    self._sb.table("agent_events")
                    .select("payload")
                    .eq("scan_id", scan_id)
                    .order("timestamp")
                    .execute()
                    .data
                )
                return [AgentEvent.model_validate(r["payload"]) for r in rows]
            with self._sqlite() as con:
                rows = con.execute(
                    "SELECT payload FROM agent_events WHERE scan_id = ?"
                    " ORDER BY \"timestamp\"",
                    (scan_id,),
                ).fetchall()
            return [AgentEvent.model_validate_json(r[0]) for r in rows]
        except Exception:
            return []

    # ── evidence_artifacts ───────────────────────────────────────────────

    def record_artifact(
        self, scan_id: str, kind: str, path: str, sha256: str, meta: dict | None = None
    ) -> None:
        """Insert an immutable evidence_artifacts row."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            if self.enabled:
                self._sb.table("evidence_artifacts").insert(
                    {
                        "id": str(uuid.uuid4()),
                        "scan_id": scan_id,
                        "kind": kind,
                        "path": path,
                        "sha256": sha256,
                        "created_at": now,
                        "meta": meta or {},
                    }
                ).execute()
                return
            with self._sqlite() as con:
                con.execute(
                    "INSERT INTO evidence_artifacts"
                    " (id, scan_id, kind, path, sha256, created_at, meta)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()),
                        scan_id,
                        kind,
                        path,
                        sha256,
                        now,
                        json.dumps(meta or {}),
                    ),
                )
        except Exception:
            pass

    # ── sleeper_monitors ─────────────────────────────────────────────────

    def register_monitor(
        self, target_url: str, baseline_hash: str, baseline_gateway: str | None
    ) -> None:
        """Persist a day-1 baseline row into sleeper_monitors."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            if self.enabled:
                self._sb.table("sleeper_monitors").insert(
                    {
                        "id": str(uuid.uuid4()),
                        "target_url": target_url,
                        "baseline_hash": baseline_hash,
                        "baseline_gateway": baseline_gateway,
                        "registered_at": now,
                    }
                ).execute()
                return
            with self._sqlite() as con:
                con.execute(
                    "INSERT INTO sleeper_monitors"
                    " (id, target_url, baseline_hash, baseline_gateway,"
                    "  registered_at) VALUES (?,?,?,?,?)",
                    (str(uuid.uuid4()), target_url, baseline_hash,
                     baseline_gateway, now),
                )
        except Exception:
            pass

    def get_monitor(self, target_url: str) -> dict[str, Any] | None:
        """Latest monitor row for a target_url, or None."""
        try:
            if self.enabled:
                rows = (
                    self._sb.table("sleeper_monitors")
                    .select("*")
                    .eq("target_url", target_url)
                    .order("registered_at", desc=True)
                    .limit(1)
                    .execute()
                    .data
                )
                return rows[0] if rows else None
            with self._sqlite() as con:
                con.row_factory = sqlite3.Row
                row = con.execute(
                    "SELECT * FROM sleeper_monitors WHERE target_url = ?"
                    " ORDER BY registered_at DESC LIMIT 1",
                    (target_url,),
                ).fetchone()
            if row is None:
                return None
            d = dict(row)
            d["history"] = json.loads(d.get("history") or "[]")
            return d
        except Exception:
            return None

    def update_monitor(self, target_url: str, check: SleeperCheckResult) -> None:
        """Record a drift check: last_* fields + history append + alert flag."""
        row = self.get_monitor(target_url)
        if row is None:
            return
        history = list(row.get("history") or [])
        history.append(check.model_dump(mode="json"))
        history = history[-200:]  # cap growth
        now = datetime.now(timezone.utc).isoformat()
        alert = bool(row.get("alert_triggered")) or check.alert_triggered
        try:
            if self.enabled:
                self._sb.table("sleeper_monitors").update(
                    {
                        "last_checked_at": now,
                        "last_hash": check.current_hash,
                        "alert_triggered": alert,
                        "history": history,
                    }
                ).eq("id", row["id"]).execute()
                return
            with self._sqlite() as con:
                con.execute(
                    "UPDATE sleeper_monitors SET last_checked_at = ?,"
                    " last_hash = ?, alert_triggered = ?, history = ? WHERE id = ?",
                    (now, check.current_hash, int(alert),
                     json.dumps(history), row["id"]),
                )
        except Exception:
            pass


store = EvidenceStore()
