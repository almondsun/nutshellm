"""SQLite-backed temporary jobs, quotas, and content-free aggregate metrics."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def _now() -> datetime:
    return datetime.now(UTC)


class Store:
    def __init__(self, path: str):
        self.path = str(Path(path).expanduser())
        self._lock = threading.RLock()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA secure_delete=ON")
        return conn

    def initialize(self) -> None:
        with self._lock, self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    owner_key TEXT,
                    scenario_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    input_json TEXT,
                    result_json TEXT,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs(status, created_at);
                CREATE TABLE IF NOT EXISTS quotas (
                    quota_key TEXT NOT NULL,
                    day TEXT NOT NULL,
                    runs INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (quota_key, day)
                );
                CREATE TABLE IF NOT EXISTS metrics (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    scenario_id TEXT,
                    mode TEXT NOT NULL,
                    original_tokens INTEGER NOT NULL,
                    optimized_tokens INTEGER NOT NULL,
                    saved_tokens INTEGER NOT NULL,
                    quality_status TEXT NOT NULL,
                    fallback TEXT,
                    latency_ms INTEGER NOT NULL,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0,
                    estimated_run_cost_usd REAL NOT NULL DEFAULT 0
                );
                """
            )
            job_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "owner_key" not in job_columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN owner_key TEXT")
            metric_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(metrics)").fetchall()
            }
            if "estimated_run_cost_usd" not in metric_columns:
                conn.execute(
                    "ALTER TABLE metrics ADD COLUMN estimated_run_cost_usd "
                    "REAL NOT NULL DEFAULT 0"
                )
            conn.execute("UPDATE jobs SET status='queued' WHERE status='running'")

    def enqueue(
        self,
        job_id: str,
        owner_key: str,
        payload: dict[str, Any],
        ttl_seconds: int,
    ) -> dict[str, str]:
        created = _now()
        expires = created + timedelta(seconds=ttl_seconds)
        with self._lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs
                    (id, owner_key, scenario_id, status, created_at, expires_at, input_json)
                VALUES (?, ?, ?, 'queued', ?, ?, ?)
                """,
                (
                    job_id,
                    owner_key,
                    payload.get("scenario_id"),
                    created.isoformat(),
                    expires.isoformat(),
                    json.dumps(payload),
                ),
            )
        return {"created_at": created.isoformat(), "expires_at": expires.isoformat()}

    def claim_next(self) -> tuple[str, dict[str, Any], str] | None:
        with self._lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "DELETE FROM jobs WHERE status='queued' AND expires_at < ?",
                (_now().isoformat(),),
            )
            row = conn.execute(
                "SELECT id, input_json, expires_at FROM jobs WHERE status='queued' "
                "ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                conn.execute("COMMIT")
                return None
            conn.execute("UPDATE jobs SET status='running' WHERE id=?", (row["id"],))
            conn.execute("COMMIT")
            return row["id"], json.loads(row["input_json"]), row["expires_at"]

    def complete(
        self, job_id: str, result: dict[str, Any], ttl_seconds: int = 3600
    ) -> None:
        metrics = result["metrics"]
        result_expires = _now() + timedelta(seconds=ttl_seconds)
        with self._lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE jobs SET status='complete', result_json=?, input_json=NULL, "
                "expires_at=? WHERE id=?",
                (json.dumps(result), result_expires.isoformat(), job_id),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO metrics
                    (id, created_at, scenario_id, mode, original_tokens,
                     optimized_tokens, saved_tokens, quality_status, fallback,
                     latency_ms, estimated_cost_usd, estimated_run_cost_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    _now().isoformat(),
                    result.get("scenario_id"),
                    result["mode"],
                    metrics["original_input_tokens"],
                    metrics["optimized_input_tokens"],
                    metrics["total_tokens_saved"],
                    result["validation"]["status"],
                    result.get("fallback"),
                    metrics["total_latency_ms"],
                    metrics["estimated_input_cost_saved_usd"],
                    metrics["estimated_total_run_cost_usd"],
                ),
            )
            conn.execute("COMMIT")

    def fail(self, job_id: str, error: str) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                "UPDATE jobs SET status='failed', error=?, input_json=NULL WHERE id=?",
                (error[:500], job_id),
            )

    def get_job(self, job_id: str, owner_key: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, status, created_at, expires_at, result_json, error "
                "FROM jobs WHERE id=? AND owner_key=?",
                (job_id, owner_key),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error": row["error"],
        }

    def consume_quota(
        self,
        client_keys: tuple[str, ...],
        per_client_limit: int,
        global_limit: int,
        global_budget_usd: float,
        run_budget_reservation_usd: float,
    ) -> tuple[bool, str]:
        day = _now().date().isoformat()
        with self._lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            client_runs = [
                self._quota_count(conn, client_key, day)
                for client_key in client_keys
            ]
            global_runs = self._quota_count(conn, "__global__", day)
            if any(runs >= per_client_limit for runs in client_runs):
                conn.execute("ROLLBACK")
                return False, "daily client run limit reached"
            if global_runs >= global_limit:
                conn.execute("ROLLBACK")
                return False, "public demo daily run limit reached"
            reserved_after_accept = run_budget_reservation_usd * (global_runs + 1)
            if global_budget_usd > 0 and reserved_after_accept > global_budget_usd:
                conn.execute("ROLLBACK")
                return False, "public demo daily budget reached"
            for key in (*client_keys, "__global__"):
                conn.execute(
                    """
                    INSERT INTO quotas (quota_key, day, runs) VALUES (?, ?, 1)
                    ON CONFLICT(quota_key, day) DO UPDATE SET runs=runs+1
                    """,
                    (key, day),
                )
            conn.execute("COMMIT")
            return True, ""

    @staticmethod
    def _quota_count(conn: sqlite3.Connection, key: str, day: str) -> int:
        row = conn.execute(
            "SELECT runs FROM quotas WHERE quota_key=? AND day=?", (key, day)
        ).fetchone()
        return int(row[0]) if row else 0

    def purge_expired(self) -> int:
        with self._lock, self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM jobs WHERE status != 'running' AND expires_at < ?",
                (_now().isoformat(),),
            )
            if cursor.rowcount:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            return cursor.rowcount

    def aggregate(self) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS runs,
                       COALESCE(SUM(original_tokens), 0) AS original_tokens,
                       COALESCE(SUM(optimized_tokens), 0) AS optimized_tokens,
                       COALESCE(SUM(saved_tokens), 0) AS saved_tokens,
                       COALESCE(SUM(estimated_cost_usd), 0) AS cost_saved,
                       COALESCE(AVG(latency_ms), 0) AS avg_latency_ms,
                       SUM(CASE WHEN quality_status='passed' THEN 1 ELSE 0 END) AS passed
                FROM metrics
                """
            ).fetchone()
        return dict(row)
