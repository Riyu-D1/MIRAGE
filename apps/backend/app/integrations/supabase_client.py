"""Supabase evidence store (T6 — SQLite fallback implemented).

Supabase Postgres when settings.supabase_enabled, else a local SQLite
fallback at artifacts/mirage.db with identical table names so the rest of
the codebase never branches. See supabase/migrations/001_initial_schema.sql.

Remaining TODO(T6): Supabase code paths (supabase-py client + Realtime) —
same method signatures, same row shapes.
"""
import json
import sqlite3
from pathlib import Path

from ..config import settings
from ..schemas import AgentEvent, ScanResult

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
    """Persistence for scans, agent events, and evidence artifacts.

    Uses Supabase when keyed; SQLite otherwise. All methods are safe no-ops
    on write failure — persistence must never break a scan.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.enabled: bool = settings.supabase_enabled
        self.db_path = db_path or settings.sqlite_path
        if self.enabled:
            # TODO(T6): init supabase-py client with SUPABASE_URL +
            # SUPABASE_SERVICE_ROLE_KEY here.
            pass
        else:
            with self._sqlite() as con:
                con.executescript(_SQLITE_DDL)

    def _sqlite(self) -> sqlite3.Connection:
        """Connection to the SQLite fallback DB (creates parent dir)."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def upsert_scan(self, scan: ScanResult) -> None:
        """Upsert a scan row (full ScanResult stored in `result`)."""
        try:
            if self.enabled:
                # TODO(T6): supabase.table("scans").upsert({...})
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
        except sqlite3.Error:
            pass

    def get_scan(self, scan_id: str) -> ScanResult | None:
        """Load a scan row and hydrate ScanResult from `result`."""
        try:
            if self.enabled:
                # TODO(T6): supabase.table("scans").select("result").eq("id", scan_id)
                return None
            with self._sqlite() as con:
                row = con.execute(
                    "SELECT result FROM scans WHERE id = ?", (scan_id,)
                ).fetchone()
            return ScanResult.model_validate_json(row[0]) if row else None
        except (sqlite3.Error, ValueError):
            return None

    def insert_event(self, event: AgentEvent) -> None:
        """Insert an AgentEvent (drives SSE replay + Realtime when keyed)."""
        try:
            if self.enabled:
                # TODO(T6): supabase.table("agent_events").insert({...})
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
        except sqlite3.Error:
            pass

    def list_events(self, scan_id: str) -> list[AgentEvent]:
        """Ordered events for a scan (SSE replay for late subscribers)."""
        try:
            if self.enabled:
                # TODO(T6): supabase select + order by timestamp
                return []
            with self._sqlite() as con:
                rows = con.execute(
                    "SELECT payload FROM agent_events WHERE scan_id = ?"
                    " ORDER BY \"timestamp\"",
                    (scan_id,),
                ).fetchall()
            return [AgentEvent.model_validate_json(r[0]) for r in rows]
        except (sqlite3.Error, ValueError):
            return []

    def record_artifact(
        self, scan_id: str, kind: str, path: str, sha256: str, meta: dict | None = None
    ) -> None:
        """Insert an immutable evidence_artifacts row."""
        import uuid
        from datetime import datetime, timezone

        try:
            if self.enabled:
                # TODO(T6): supabase.table("evidence_artifacts").insert({...})
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
                        datetime.now(timezone.utc).isoformat(),
                        json.dumps(meta or {}),
                    ),
                )
        except sqlite3.Error:
            pass


store = EvidenceStore()
