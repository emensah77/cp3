from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from google_ads_ops.credentials import GoogleAdsCredential
from google_ads_ops.models import APPROVED, SYNCED
from google_ads_ops.provider import MockGoogleAdsProvider
from google_ads_ops.sqlite_store import SQLiteGoogleAdsStore
from google_ads_ops.storage import load_conversions, load_plan
from google_ads_ops.sync import sync_approved_mutations, upload_offline_conversions


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "campaign_plan.json"
CONVERSIONS = ROOT / "data" / "offline_conversions.json"


def credential() -> GoogleAdsCredential:
    return GoogleAdsCredential(
        developer_token="developer-token-demo",
        client_id="client",
        client_secret="secret",
        refresh_token="refresh",
        access_token="access-token-demo",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        customer_id="1234567890",
        login_customer_id="9998887777",
    )


class SQLiteStoreAndSyncTests(unittest.TestCase):
    def test_import_approve_and_sync_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteGoogleAdsStore(Path(tmp) / "ads.db")
            try:
                plan = load_plan(PLAN)
                store.migrate()
                store.import_mutations(customer_id=plan.customer_id, mutations=plan.campaigns, actor_id="media-lead")
                store.approve(mutation_id="mut-001", actor_id="director", approved_at=datetime(2026, 6, 8, 12))

                first = sync_approved_mutations(
                    store,
                    credential=credential(),
                    provider=MockGoogleAdsProvider(),
                    now=datetime(2026, 6, 8, 13),
                    worker_id="worker-a",
                )
                second = sync_approved_mutations(
                    store,
                    credential=credential(),
                    provider=MockGoogleAdsProvider(),
                    now=datetime(2026, 6, 8, 13),
                    worker_id="worker-b",
                )

                self.assertEqual(first, 1)
                self.assertEqual(second, 0)
                self.assertEqual(store.mutation_receipt_count(), 1)
                self.assertEqual(store.list_mutations()[0].state, SYNCED)
                self.assertEqual(store.audit_count(), 3)
            finally:
                store.close()

    def test_leases_prevent_duplicate_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ads.db"
            first = SQLiteGoogleAdsStore(db)
            second = SQLiteGoogleAdsStore(db)
            try:
                plan = load_plan(PLAN)
                first.migrate()
                first.import_mutations(customer_id=plan.customer_id, mutations=plan.campaigns, actor_id="media-lead")
                first.approve(mutation_id="mut-001", actor_id="director", approved_at=datetime(2026, 6, 8, 12))
                first.approve(mutation_id="mut-002", actor_id="director", approved_at=datetime(2026, 6, 8, 12))

                claimed_a = first.claim_approved(
                    now=datetime(2026, 6, 8, 13),
                    worker_id="worker-a",
                    lease_seconds=300,
                    limit=1,
                )
                claimed_b = second.claim_approved(
                    now=datetime(2026, 6, 8, 13),
                    worker_id="worker-b",
                    lease_seconds=300,
                    limit=10,
                )

                self.assertEqual([item.id for item in claimed_a], ["mut-001"])
                self.assertEqual([item.id for item in claimed_b], ["mut-002"])
                self.assertEqual(claimed_b[0].state, APPROVED)
            finally:
                first.close()
                second.close()

    def test_conversion_upload_records_successes_once_and_errors_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteGoogleAdsStore(Path(tmp) / "ads.db")
            try:
                store.migrate()
                conversions = load_conversions(CONVERSIONS)

                uploaded, errors = upload_offline_conversions(
                    store,
                    conversions=conversions,
                    credential=credential(),
                    provider=MockGoogleAdsProvider(),
                    now=datetime(2026, 6, 8, 13),
                    debug_enabled=True,
                )
                uploaded_again, errors_again = upload_offline_conversions(
                    store,
                    conversions=conversions,
                    credential=credential(),
                    provider=MockGoogleAdsProvider(),
                    now=datetime(2026, 6, 8, 13),
                    debug_enabled=True,
                )

                self.assertEqual((uploaded, errors), (1, 1))
                self.assertEqual((uploaded_again, errors_again), (0, 1))
                self.assertEqual(store.conversion_receipt_count(), 1)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
