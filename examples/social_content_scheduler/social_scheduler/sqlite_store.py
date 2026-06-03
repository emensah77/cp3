"""SQLite-backed scheduler storage with migrations and job leases."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from .credentials import OAuthCredential
from .models import APPROVED, FAILED, POSTED, PostReceipt, ScheduledPost


SCHEMA_VERSION = 2


class SQLiteScheduleStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, isolation_level=None)
        self.connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self.connection.close()

    def migrate(self) -> None:
        with self.transaction():
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    text TEXT NOT NULL,
                    campaign TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approved_by TEXT,
                    approved_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    lease_owner TEXT,
                    lease_until TEXT
                )
                """
            )
            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_scheduled_posts_due
                ON scheduled_posts(status, scheduled_at, lease_until)
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS post_receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    posted_at TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    status TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    provider_post_id TEXT NOT NULL,
                    error TEXT,
                    canonical_url TEXT
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_credentials (
                    account_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    PRIMARY KEY(account_id, platform)
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
                """
                INSERT OR IGNORE INTO schema_migrations(version, applied_at)
                VALUES (?, ?)
                """,
                (SCHEMA_VERSION, datetime.now(UTC).isoformat()),
            )

    def transaction(self) -> sqlite3.Connection:
        self.connection.execute("BEGIN IMMEDIATE")
        return _Transaction(self.connection)  # type: ignore[return-value]

    def insert_scheduled(self, scheduled: Iterable[ScheduledPost]) -> None:
        with self.transaction():
            for item in scheduled:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO scheduled_posts (
                        draft_id, platform, text, campaign, scheduled_at, status,
                        approved_by, approved_at, attempts, last_error, idempotency_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.draft_id,
                        item.platform,
                        item.text,
                        item.campaign,
                        item.scheduled_at.isoformat(),
                        item.status,
                        item.approved_by,
                        item.approved_at.isoformat() if item.approved_at else None,
                        item.attempts,
                        item.last_error,
                        item.idempotency_key(),
                    ),
                )

    def approve(self, *, draft_id: str, reviewer: str, approved_at: datetime) -> None:
        with self.transaction():
            cursor = self.connection.execute(
                """
                UPDATE scheduled_posts
                SET status = ?, approved_by = ?, approved_at = ?, last_error = NULL
                WHERE draft_id = ? AND status != ?
                """,
                (APPROVED, reviewer, approved_at.isoformat(), draft_id, POSTED),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"No approvable scheduled post found for draft id: {draft_id}")
            self.record_audit_event(
                event="post.approved",
                actor_id=reviewer,
                target=draft_id,
                occurred_at=approved_at,
                metadata='{"source":"sqlite"}',
                in_transaction=True,
            )

    def claim_due(
        self,
        *,
        now: datetime,
        worker_id: str,
        lease_seconds: int,
        limit: int,
    ) -> list[ScheduledPost]:
        lease_until = now + timedelta(seconds=lease_seconds)
        with self.transaction():
            rows = self.connection.execute(
                """
                SELECT *
                FROM scheduled_posts
                WHERE status = ?
                  AND scheduled_at <= ?
                  AND (lease_until IS NULL OR lease_until <= ?)
                ORDER BY scheduled_at, id
                LIMIT ?
                """,
                (APPROVED, now.isoformat(), now.isoformat(), limit),
            ).fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                self.connection.execute(
                    f"""
                    UPDATE scheduled_posts
                    SET lease_owner = ?, lease_until = ?
                    WHERE id IN ({placeholders})
                    """,
                    (worker_id, lease_until.isoformat(), *ids),
                )
            return [_scheduled_from_row(row) for row in rows]

    def complete_post(self, item: ScheduledPost, receipt: PostReceipt) -> bool:
        with self.transaction():
            try:
                self.connection.execute(
                    """
                    INSERT INTO post_receipts (
                        draft_id, platform, posted_at, destination, status,
                        idempotency_key, provider_post_id, error, canonical_url
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.draft_id,
                        receipt.platform,
                        receipt.posted_at.isoformat(),
                        receipt.destination,
                        receipt.status,
                        receipt.idempotency_key,
                        receipt.provider_post_id,
                        receipt.error,
                        receipt.canonical_url,
                    ),
                )
                inserted = True
            except sqlite3.IntegrityError:
                inserted = False
            self.connection.execute(
                """
                UPDATE scheduled_posts
                SET status = ?, attempts = attempts + 1, last_error = NULL,
                    lease_owner = NULL, lease_until = NULL
                WHERE idempotency_key = ?
                """,
                (POSTED, item.idempotency_key()),
            )
            return inserted

    def fail_post(self, item: ScheduledPost, *, error: str) -> None:
        with self.transaction():
            self.connection.execute(
                """
                UPDATE scheduled_posts
                SET status = ?, attempts = attempts + 1, last_error = ?,
                    lease_owner = NULL, lease_until = NULL
                WHERE idempotency_key = ?
                """,
                (FAILED, error, item.idempotency_key()),
            )

    def list_scheduled(self) -> list[ScheduledPost]:
        rows = self.connection.execute(
            "SELECT * FROM scheduled_posts ORDER BY scheduled_at, id"
        ).fetchall()
        return [_scheduled_from_row(row) for row in rows]

    def receipt_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM post_receipts").fetchone()
        return int(row["count"])

    def save_credential(self, credential: OAuthCredential) -> None:
        with self.transaction():
            self.connection.execute(
                """
                INSERT INTO oauth_credentials (
                    account_id, platform, access_token, refresh_token, expires_at, scopes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, platform) DO UPDATE SET
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    expires_at = excluded.expires_at,
                    scopes = excluded.scopes
                """,
                (
                    credential.account_id,
                    credential.platform,
                    credential.access_token,
                    credential.refresh_token,
                    credential.expires_at.isoformat(),
                    ",".join(credential.scopes),
                ),
            )

    def load_credential(self, *, account_id: str, platform: str) -> OAuthCredential | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM oauth_credentials
            WHERE account_id = ? AND platform = ?
            """,
            (account_id, platform),
        ).fetchone()
        if row is None:
            return None
        return OAuthCredential(
            account_id=row["account_id"],
            platform=row["platform"],
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            expires_at=datetime.fromisoformat(row["expires_at"]),
            scopes=tuple(scope for scope in row["scopes"].split(",") if scope),
        )

    def record_audit_event(
        self,
        *,
        event: str,
        actor_id: str,
        target: str,
        occurred_at: datetime,
        metadata: str | None = None,
        in_transaction: bool = False,
    ) -> None:
        def insert() -> None:
            self.connection.execute(
                """
                INSERT INTO audit_events(event, actor_id, target, occurred_at, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event, actor_id, target, occurred_at.isoformat(), metadata),
            )

        if in_transaction:
            insert()
        else:
            with self.transaction():
                insert()

    def audit_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM audit_events").fetchone()
        return int(row["count"])


class _Transaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __enter__(self) -> sqlite3.Connection:
        return self.connection

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.connection.execute("COMMIT")
        else:
            self.connection.execute("ROLLBACK")


def _scheduled_from_row(row: sqlite3.Row) -> ScheduledPost:
    return ScheduledPost.from_dict(
        {
            "draft_id": row["draft_id"],
            "platform": row["platform"],
            "text": row["text"],
            "campaign": row["campaign"],
            "scheduled_at": row["scheduled_at"],
            "status": row["status"],
            "approved_by": row["approved_by"],
            "approved_at": row["approved_at"],
            "attempts": row["attempts"],
            "last_error": row["last_error"],
        }
    )
