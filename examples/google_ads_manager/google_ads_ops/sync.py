"""Workers for approved Google Ads mutations and conversion uploads."""

from __future__ import annotations

from datetime import datetime

from .credentials import GoogleAdsCredential
from .models import CampaignMutation, OfflineConversion
from .provider import MockGoogleAdsProvider
from .sqlite_store import SQLiteGoogleAdsStore


def sync_approved_mutations(
    store: SQLiteGoogleAdsStore,
    *,
    credential: GoogleAdsCredential,
    provider: MockGoogleAdsProvider,
    now: datetime,
    worker_id: str,
    limit: int = 10,
) -> int:
    claimed = store.claim_approved(now=now, worker_id=worker_id, lease_seconds=300, limit=limit)
    synced = 0
    for mutation in claimed:
        response = provider.mutate_campaigns(
            [mutation],
            credential=credential,
            validate_only=False,
            partial_failure=True,
            now=now,
        )
        if response.errors:
            store.fail_mutation(mutation_id=mutation.id, error=response.errors[0].message)
            continue
        for receipt in response.receipts:
            if store.complete_mutation(receipt):
                synced += 1
    return synced


def upload_offline_conversions(
    store: SQLiteGoogleAdsStore,
    *,
    conversions: list[OfflineConversion],
    credential: GoogleAdsCredential,
    provider: MockGoogleAdsProvider,
    now: datetime,
    debug_enabled: bool,
) -> tuple[int, int]:
    response = provider.upload_click_conversions(
        conversions,
        credential=credential,
        debug_enabled=debug_enabled,
        partial_failure=True,
        now=now,
    )
    inserted = store.record_conversion_receipts(response.receipts)
    return inserted, len(response.errors)

