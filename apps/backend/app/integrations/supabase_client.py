"""Supabase evidence store (T6).

Supabase Postgres when settings.supabase_enabled, else a local SQLite
fallback at artifacts/mirage.db with identical table names so the rest of
the codebase never branches. See supabase/migrations/001_initial_schema.sql.
"""
import sqlite3
from pathlib import Path

from ..config import settings
from ..schemas import AgentEvent, ScanResult


class EvidenceStore:
    """Persistence shell for scans, agent events, and evidence artifacts."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.enabled: bool = settings.supabase_enabled
        self.db_path = db_path or settings.sqlite_path
        # TODO(T6): when enabled, init a supabase-py client with
        # SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY; else ensure the SQLite
        # fallback schema exists (mirror of 001_initial_schema.sql).

    def _sqlite(self) -> sqlite3.Connection:
        """Connection to the SQLite fallback DB (creates parent dir)."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def upsert_scan(self, scan: ScanResult) -> None:
        """TODO(T6): upsert into `scans` (result jsonb column)."""
        raise NotImplementedError("T6 — implement per docs/TASKS.md")

    def get_scan(self, scan_id: str) -> ScanResult | None:
        """TODO(T6): load scan row and hydrate ScanResult from jsonb."""
        raise NotImplementedError("T6 — implement per docs/TASKS.md")

    def insert_event(self, event: AgentEvent) -> None:
        """TODO(T6): insert into `agent_events` (drives SSE + Realtime)."""
        raise NotImplementedError("T6 — implement per docs/TASKS.md")

    def list_events(self, scan_id: str) -> list[AgentEvent]:
        """TODO(T6): ordered events for a scan (SSE replay for late joins)."""
        raise NotImplementedError("T6 — implement per docs/TASKS.md")

    def record_artifact(
        self, scan_id: str, kind: str, path: str, sha256: str, meta: dict | None = None
    ) -> None:
        """TODO(T6): insert into `evidence_artifacts` (immutable vault row)."""
        raise NotImplementedError("T6 — implement per docs/TASKS.md")


store = EvidenceStore()
