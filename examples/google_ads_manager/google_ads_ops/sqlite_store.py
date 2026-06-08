"""SQLite store for Google Ads campaign mutations and conversion uploads."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from .models import APPROVED, FAILED, LEASED, PENDING_APPROVAL, SYNCED, CampaignMutation, ConversionReceipt, MutationReceipt, OfflineConversion


SCHEMA_VERSION = 1


class SQLiteGoogleAdsStore:
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
                CREATE TABLE IF NOT EXISTS campaign_mutations (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    daily_budget_micros INTEGER NOT NULL,
                    final_url TEXT NOT NULL,
                    headlines TEXT NOT NULL,
                    descriptions TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    resource_name TEXT,
                    last_error TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    lease_owner TEXT,
                    lease_until TEXT,
                    approved_by TEXT,
                    approved_at TEXT
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mutation_receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutation_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    resource_name TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    synced_at TEXT NOT NULL
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversion_receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversion_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    uploaded_at TEXT NOT NULL,
                    error TEXT
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

    def import_mutations(self, *, customer_id: str, mutations: Iterable[CampaignMutation], actor_id: str) -> None:
        with self.transaction():
            for mutation in mutations:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO campaign_mutations (
                        id, customer_id, name, channel, status, daily_budget_micros,
                        final_url, headlines, descriptions, keywords, state, attempts,
                        resource_name, last_error, idempotency_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mutation.id,
                        customer_id,
                        mutation.name,
                        mutation.channel,
                        mutation.status,
                        mutation.daily_budget_micros,
                        mutation.final_url,
                        "\n".join(mutation.headlines),
                        "\n".join(mutation.descriptions),
                        "\n".join(mutation.keywords),
                        PENDING_APPROVAL,
                        mutation.attempts,
                        mutation.resource_name,
                        mutation.last_error,
                        mutation.idempotency_key(customer_id),
                    ),
                )
                self._record_audit(
                    event="campaign.imported",
                    actor_id=actor_id,
                    target=mutation.id,
                    occurred_at=datetime.now(UTC),
                    metadata=f"customer_id={customer_id}",
                )

    def approve(self, *, mutation_id: str, actor_id: str, approved_at: datetime) -> None:
        with self.transaction():
            cursor = self.connection.execute(
                """
                UPDATE campaign_mutations
                SET state = ?, approved_by = ?, approved_at = ?, last_error = NULL
                WHERE id = ? AND state IN (?, ?)
                """,
                (APPROVED, actor_id, approved_at.isoformat(), mutation_id, PENDING_APPROVAL, FAILED),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"No approvable campaign mutation found: {mutation_id}")
            self._record_audit(
                event="campaign.approved",
                actor_id=actor_id,
                target=mutation_id,
                occurred_at=approved_at,
                metadata=None,
            )

    def claim_approved(self, *, now: datetime, worker_id: str, lease_seconds: int, limit: int) -> list[CampaignMutation]:
        lease_until = now + timedelta(seconds=lease_seconds)
        with self.transaction():
            rows = self.connection.execute(
                """
                SELECT *
                FROM campaign_mutations
                WHERE state = ?
                  AND (lease_until IS NULL OR lease_until <= ?)
                ORDER BY id
                LIMIT ?
                """,
                (APPROVED, now.isoformat(), limit),
            ).fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                self.connection.execute(
                    f"UPDATE campaign_mutations SET state = ?, lease_owner = ?, lease_until = ? WHERE id IN ({placeholders})",
                    (LEASED, worker_id, lease_until.isoformat(), *ids),
                )
            return [_mutation_from_row(row) for row in rows]

    def complete_mutation(self, receipt: MutationReceipt) -> bool:
        with self.transaction():
            try:
                self.connection.execute(
                    """
                    INSERT INTO mutation_receipts (
                        mutation_id, customer_id, resource_name, request_id, idempotency_key, synced_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.mutation_id,
                        receipt.customer_id,
                        receipt.resource_name,
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
                UPDATE campaign_mutations
                SET state = ?, attempts = attempts + 1, resource_name = ?,
                    last_error = NULL, lease_owner = NULL, lease_until = NULL
                WHERE id = ?
                """,
                (SYNCED, receipt.resource_name, receipt.mutation_id),
            )
            return inserted

    def fail_mutation(self, *, mutation_id: str, error: str) -> None:
        with self.transaction():
            self.connection.execute(
                """
                UPDATE campaign_mutations
                SET state = ?, attempts = attempts + 1, last_error = ?,
                    lease_owner = NULL, lease_until = NULL
                WHERE id = ?
                """,
                (FAILED, error, mutation_id),
            )

    def record_conversion_receipts(self, receipts: list[ConversionReceipt]) -> int:
        inserted = 0
        with self.transaction():
            for receipt in receipts:
                try:
                    self.connection.execute(
                        """
                        INSERT INTO conversion_receipts (
                            conversion_id, customer_id, status, request_id, idempotency_key, uploaded_at, error
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            receipt.conversion_id,
                            receipt.customer_id,
                            receipt.status,
                            receipt.request_id,
                            receipt.idempotency_key,
                            receipt.uploaded_at.isoformat(),
                            receipt.error,
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue
        return inserted

    def list_mutations(self) -> list[CampaignMutation]:
        rows = self.connection.execute("SELECT * FROM campaign_mutations ORDER BY id").fetchall()
        return [_mutation_from_row(row) for row in rows]

    def mutation_receipt_count(self) -> int:
        return _count(self.connection, "mutation_receipts")

    def conversion_receipt_count(self) -> int:
        return _count(self.connection, "conversion_receipts")

    def audit_count(self) -> int:
        return _count(self.connection, "audit_events")

    def _record_audit(
        self,
        *,
        event: str,
        actor_id: str,
        target: str,
        occurred_at: datetime,
        metadata: str | None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO audit_events(event, actor_id, target, occurred_at, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event, actor_id, target, occurred_at.isoformat(), metadata),
        )


class _Transaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __enter__(self) -> sqlite3.Connection:
        return self.connection

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.connection.execute("COMMIT" if exc_type is None else "ROLLBACK")


def _mutation_from_row(row: sqlite3.Row) -> CampaignMutation:
    return CampaignMutation(
        id=row["id"],
        name=row["name"],
        channel=row["channel"],
        status=row["status"],
        daily_budget_micros=int(row["daily_budget_micros"]),
        final_url=row["final_url"],
        headlines=row["headlines"].split("\n"),
        descriptions=row["descriptions"].split("\n"),
        keywords=row["keywords"].split("\n"),
        state=row["state"],
        attempts=int(row["attempts"]),
        resource_name=row["resource_name"],
        last_error=row["last_error"],
    )


def _count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"])

