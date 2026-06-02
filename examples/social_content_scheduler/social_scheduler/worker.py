"""Worker helpers for leased SQLite posting."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import PostReceipt
from .providers import MockSocialProvider
from .sqlite_store import SQLiteScheduleStore


def post_due_from_store(
    store: SQLiteScheduleStore,
    *,
    now: datetime,
    worker_id: str,
    outbox_path: Path,
    lease_seconds: int = 300,
    limit: int = 10,
    provider: MockSocialProvider | None = None,
) -> int:
    provider = provider or MockSocialProvider()
    claimed = store.claim_due(
        now=now,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        limit=limit,
    )
    posted = 0
    for item in claimed:
        key = item.idempotency_key()
        try:
            result = provider.publish(item, idempotency_key=key)
        except Exception as exc:
            store.fail_post(item, error=str(exc))
            continue
        receipt = PostReceipt(
            draft_id=item.draft_id,
            platform=item.platform,
            posted_at=now,
            destination=str(outbox_path),
            status="posted",
            idempotency_key=key,
            provider_post_id=result.provider_post_id,
        )
        if store.complete_post(item, receipt):
            posted += 1
    return posted

