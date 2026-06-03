"""Worker helpers for leased SQLite posting."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import PostReceipt
from .observability import JsonEventLogger, Metrics
from .providers import MockSocialProvider, ProviderRegistry, SocialProvider
from .sqlite_store import SQLiteScheduleStore


def post_due_from_store(
    store: SQLiteScheduleStore,
    *,
    now: datetime,
    worker_id: str,
    outbox_path: Path,
    lease_seconds: int = 300,
    limit: int = 10,
    provider: SocialProvider | None = None,
    provider_registry: ProviderRegistry | None = None,
    account_id: str | None = None,
    metrics: Metrics | None = None,
    event_logger: JsonEventLogger | None = None,
) -> int:
    provider = provider or MockSocialProvider()
    metrics = metrics or Metrics()
    claimed = store.claim_due(
        now=now,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        limit=limit,
    )
    posted = 0
    for item in claimed:
        key = item.idempotency_key()
        item_provider = provider_registry.get(item.platform) if provider_registry else provider
        credential = store.load_credential(account_id=account_id, platform=item.platform) if account_id else None
        if credential and credential.is_expired(now):
            credential = credential.refresh(now=now)
            store.save_credential(credential)
        try:
            result = item_provider.publish(item, idempotency_key=key, credential=credential)
        except Exception as exc:
            store.fail_post(item, error=str(exc))
            metrics.increment("posts.failed")
            if event_logger:
                event_logger.emit(
                    event="post.failed",
                    at=now,
                    worker_id=worker_id,
                    draft_id=item.draft_id,
                    platform=item.platform,
                    error=str(exc),
                )
            continue
        receipt = PostReceipt(
            draft_id=item.draft_id,
            platform=item.platform,
            posted_at=now,
            destination=str(outbox_path),
            status="posted",
            idempotency_key=key,
            provider_post_id=result.provider_post_id,
            canonical_url=result.canonical_url,
        )
        if store.complete_post(item, receipt):
            posted += 1
            metrics.increment("posts.posted")
            if event_logger:
                event_logger.emit(
                    event="post.posted",
                    at=now,
                    worker_id=worker_id,
                    draft_id=item.draft_id,
                    platform=item.platform,
                    provider_post_id=result.provider_post_id,
                )
    return posted
