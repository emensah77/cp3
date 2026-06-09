"""SQLite store for Notion sync records, receipts, leases, and audit."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from .models import FAILED, LEASED, PENDING, SYNCED, ProjectRecord, SyncReceipt


SCHEMA_VERSION = 1


class SQLiteNotionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, isolation_level=None)
        self.connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self.connection.close()

    def transaction(self) -> "_Transaction":
        self.connection.execute("BEGIN IMMEDIATE")
        return _Transaction(self.connection)

    def migrate(self) -> None:
        with self.transaction():
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS project_records (
                    external_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    due TEXT NOT NULL,
                    url TEXT NOT NULL,
                    published INTEGER NOT NULL,
                    related_external_ids TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    next_steps TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    notion_page_id TEXT,
                    last_error TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    lease_owner TEXT,
                    lease_until TEXT
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT NOT NULL,
                    data_source_id TEXT NOT NULL,
                    notion_page_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    synced_at TEXT NOT NULL
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.now(UTC).isoformat()),
            )

    def import_records(self, records: Iterable[ProjectRecord], *, data_source_id: str, actor_id: str) -> None:
        with self.transaction():
            for record in records:
                self.connection.execute(
                    """
                    INSERT INTO project_records (
                        external_id, name, status, owner, tags, due, url, published,
                        related_external_ids, summary, next_steps, state, attempts,
                        notion_page_id, last_error, idempotency_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(external_id) DO UPDATE SET
                        name = excluded.name,
                        status = excluded.status,
                        owner = excluded.owner,
                        tags = excluded.tags,
                        due = excluded.due,
                        url = excluded.url,
                        published = excluded.published,
                        related_external_ids = excluded.related_external_ids,
                        summary = excluded.summary,
                        next_steps = excluded.next_steps,
                        state = ?,
                        last_error = NULL
                    """
                    ,
                    (
                        record.external_id,
                        record.name,
                        record.status,
                        record.owner,
                        "\n".join(record.tags),
                        record.due,
                        record.url,
                        int(record.published),
                        "\n".join(record.related_external_ids),
                        record.summary,
                        "\n".join(record.next_steps),
                        PENDING,
                        record.attempts,
                        record.notion_page_id,
                        record.last_error,
                        record.idempotency_key(data_source_id),
                        PENDING,
                    ),
                )
                self._record_audit("record.imported", actor_id, record.external_id, f"data_source_id={data_source_id}")

    def claim_pending(self, *, now: datetime, worker_id: str, lease_seconds: int, limit: int) -> list[ProjectRecord]:
        lease_until = now + timedelta(seconds=lease_seconds)
        with self.transaction():
            rows = self.connection.execute(
                """
                SELECT *
                FROM project_records
                WHERE state = ? AND (lease_until IS NULL OR lease_until <= ?)
                ORDER BY external_id
                LIMIT ?
                """,
                (PENDING, now.isoformat(), limit),
            ).fetchall()
            ids = [row["external_id"] for row in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                self.connection.execute(
                    f"UPDATE project_records SET state = ?, lease_owner = ?, lease_until = ? WHERE external_id IN ({placeholders})",
                    (LEASED, worker_id, lease_until.isoformat(), *ids),
                )
            return [_record_from_row(row) for row in rows]

    def complete(self, receipt: SyncReceipt) -> bool:
        with self.transaction():
            try:
                self.connection.execute(
                    """
                    INSERT INTO sync_receipts (
                        external_id, data_source_id, notion_page_id, request_id, idempotency_key, synced_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.external_id,
                        receipt.data_source_id,
                        receipt.notion_page_id,
                        receipt.request_id,
                        receipt.idempotency_key,
                        receipt.synced_at.isoformat(),
                    ),
                )
                inserted = True
            except sqlite3.IntegrityError:
                inserted = False
            self.connection.execute(
                """
                UPDATE project_records
                SET state = ?, attempts = attempts + 1, notion_page_id = ?,
                    last_error = NULL, lease_owner = NULL, lease_until = NULL
                WHERE external_id = ?
                """,
                (SYNCED, receipt.notion_page_id, receipt.external_id),
            )
            return inserted

    def fail(self, *, external_id: str, error: str) -> None:
        with self.transaction():
            self.connection.execute(
                """
                UPDATE project_records
                SET state = ?, attempts = attempts + 1, last_error = ?,
                    lease_owner = NULL, lease_until = NULL
                WHERE external_id = ?
                """,
                (FAILED, error, external_id),
            )

    def list_records(self) -> list[ProjectRecord]:
        rows = self.connection.execute("SELECT * FROM project_records ORDER BY external_id").fetchall()
        return [_record_from_row(row) for row in rows]

    def receipt_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM sync_receipts").fetchone()
        return int(row["count"])

    def audit_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM audit_events").fetchone()
        return int(row["count"])

    def _record_audit(self, event: str, actor_id: str, target: str, metadata: str | None) -> None:
        self.connection.execute(
            "INSERT INTO audit_events(event, actor_id, target, occurred_at, metadata) VALUES (?, ?, ?, ?, ?)",
            (event, actor_id, target, datetime.now(UTC).isoformat(), metadata),
        )


class _Transaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __enter__(self) -> sqlite3.Connection:
        return self.connection

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.connection.execute("COMMIT" if exc_type is None else "ROLLBACK")


def _record_from_row(row: sqlite3.Row) -> ProjectRecord:
    return ProjectRecord(
        external_id=row["external_id"],
        name=row["name"],
        status=row["status"],
        owner=row["owner"],
        tags=[item for item in row["tags"].split("\n") if item],
        due=row["due"],
        url=row["url"],
        published=bool(row["published"]),
        related_external_ids=[item for item in row["related_external_ids"].split("\n") if item],
        summary=row["summary"],
        next_steps=[item for item in row["next_steps"].split("\n") if item],
        state=row["state"],
        attempts=int(row["attempts"]),
        notion_page_id=row["notion_page_id"],
        last_error=row["last_error"],
    )

