"""Scheduling logic for generated social posts."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import PostDraft, ScheduledPost


def schedule_posts(
    drafts: list[PostDraft],
    *,
    start_at: datetime,
    cadence_hours: int,
) -> list[ScheduledPost]:
    if cadence_hours < 1:
        raise ValueError("cadence_hours must be at least 1")

    scheduled: list[ScheduledPost] = []
    for index, draft in enumerate(drafts):
        scheduled.append(
            ScheduledPost(
                draft_id=draft.id,
                platform=draft.platform,
                text=draft.text,
                campaign=draft.campaign,
                scheduled_at=start_at + timedelta(hours=index * cadence_hours),
            )
        )
    return scheduled


def approve_scheduled_post(
    scheduled: list[ScheduledPost],
    *,
    draft_id: str,
    reviewer: str,
    approved_at: datetime,
) -> list[ScheduledPost]:
    matched = False
    updated: list[ScheduledPost] = []
    for item in scheduled:
        if item.draft_id != draft_id:
            updated.append(item)
            continue
        if matched:
            raise ValueError(f"Multiple scheduled posts found for draft id: {draft_id}")
        matched = True
        updated.append(item.approve(reviewer=reviewer, approved_at=approved_at))

    if not matched:
        raise ValueError(f"No scheduled post found for draft id: {draft_id}")
    return updated


def calendar_lines(scheduled: list[ScheduledPost]) -> list[str]:
    ordered = sorted(scheduled, key=lambda item: (item.scheduled_at, item.platform, item.draft_id))
    return [
        f"{item.scheduled_at.isoformat()} {item.platform} {item.draft_id} {item.status}"
        for item in ordered
    ]
