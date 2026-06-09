from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from notion_sync.capabilities import INSERT_CONTENT, READ_CONTENT, NotionConnection
from notion_sync.models import SYNCED
from notion_sync.provider import MockNotionProvider
from notion_sync.sqlite_store import SQLiteNotionStore
from notion_sync.storage import load_records, load_schema
from notion_sync.sync import default_connection, sync_due_records


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "data" / "projects.json"
SCHEMA = ROOT / "data" / "notion_schema.json"


class ProviderAndSyncTests(unittest.TestCase):
    def test_provider_requires_update_capability_for_existing_page(self) -> None:
        records = load_records(RECORDS)
        schema = load_schema(SCHEMA)
        provider = MockNotionProvider()
        full = default_connection(schema.data_source_id)
        insert_only = NotionConnection(
            bot_id="bot-limited",
            token_label="limited",
            capabilities={READ_CONTENT, INSERT_CONTENT},
            shared_data_source_ids={schema.data_source_id},
        )
        provider.upsert_page(record=records[0], schema=schema, connection=full, now=datetime(2026, 6, 8, tzinfo=UTC))

        with self.assertRaises(PermissionError):
            provider.upsert_page(
                record=records[0],
                schema=schema,
                connection=insert_only,
                now=datetime(2026, 6, 8, tzinfo=UTC),
            )

    def test_sqlite_sync_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            schema = load_schema(SCHEMA)
            records = load_records(RECORDS)
            store = SQLiteNotionStore(Path(tmp) / "notion.db")
            try:
                store.migrate()
                store.import_records(records, data_source_id=schema.data_source_id, actor_id="tester")
                provider = MockNotionProvider()
                first = sync_due_records(
                    store,
                    schema=schema,
                    provider=provider,
                    connection=default_connection(schema.data_source_id),
                    now=datetime(2026, 6, 8, tzinfo=UTC),
                    worker_id="worker-a",
                )
                second = sync_due_records(
                    store,
                    schema=schema,
                    provider=provider,
                    connection=default_connection(schema.data_source_id),
                    now=datetime(2026, 6, 8, tzinfo=UTC),
                    worker_id="worker-b",
                )

                self.assertEqual(first, 2)
                self.assertEqual(second, 0)
                self.assertEqual(store.receipt_count(), 2)
                self.assertEqual([record.state for record in store.list_records()], [SYNCED, SYNCED])
                self.assertEqual(store.audit_count(), 2)
            finally:
                store.close()

    def test_leases_prevent_duplicate_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            schema = load_schema(SCHEMA)
            db = Path(tmp) / "notion.db"
            first = SQLiteNotionStore(db)
            second = SQLiteNotionStore(db)
            try:
                first.migrate()
                first.import_records(load_records(RECORDS), data_source_id=schema.data_source_id, actor_id="tester")
                claimed_a = first.claim_pending(
                    now=datetime(2026, 6, 8, tzinfo=UTC),
                    worker_id="worker-a",
                    lease_seconds=300,
                    limit=1,
                )
                claimed_b = second.claim_pending(
                    now=datetime(2026, 6, 8, tzinfo=UTC),
                    worker_id="worker-b",
                    lease_seconds=300,
                    limit=10,
                )

                self.assertEqual([item.external_id for item in claimed_a], ["proj-001"])
                self.assertEqual([item.external_id for item in claimed_b], ["proj-002"])
            finally:
                first.close()
                second.close()


if __name__ == "__main__":
    unittest.main()

