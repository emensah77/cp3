"""Mock posting layer for scheduled social posts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import APPROVED, POSTED, PostReceipt, ScheduledPost
from .providers import MockSocialProvider


def post_due(
    scheduled: list[ScheduledPost],
    *,
    now: datetime,
    outbox_path: Path,
    existing_receipts: list[PostReceipt] | None = None,
    provider: MockSocialProvider | None = None,
) -> tuple[list[ScheduledPost], list[PostReceipt]]:
    provider = provider or MockSocialProvider()
    successful_keys = {
        receipt.idempotency_key
        for receipt in existing_receipts or []
        if receipt.status == POSTED
    }
    receipts: list[PostReceipt] = []
    updated: list[ScheduledPost] = []
    for item in scheduled:
        if item.status != APPROVED or item.scheduled_at > now:
            updated.append(item)
            continue
        key = item.idempotency_key()
        if key in successful_keys:
            updated.append(item.mark_posted())
            continue
        try:
            provider_result = provider.publish(item, idempotency_key=key)
        except Exception as exc:
            failed = item.mark_failed(str(exc))
            updated.append(failed)
            receipts.append(
                PostReceipt(
                    draft_id=item.draft_id,
                    platform=item.platform,
                    posted_at=now,
                    destination=str(outbox_path),
                    status=failed.status,
                    idempotency_key=key,
                    provider_post_id="",
                    error=str(exc),
                )
            )
            continue
        posted = item.mark_posted()
        updated.append(posted)
        receipts.append(
            PostReceipt(
                draft_id=item.draft_id,
                platform=item.platform,
                posted_at=now,
                destination=str(outbox_path),
                status=posted.status,
                idempotency_key=key,
                provider_post_id=provider_result.provider_post_id,
                canonical_url=provider_result.canonical_url,
            )
        )
    return updated, receipts
