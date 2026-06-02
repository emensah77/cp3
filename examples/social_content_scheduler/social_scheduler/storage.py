"""JSON storage helpers for the social scheduler example."""

from __future__ import annotations

import json
from pathlib import Path

from .models import CampaignBrief, PostDraft, PostReceipt, ScheduledPost


def load_brief(path: Path) -> CampaignBrief:
    return CampaignBrief.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_drafts(path: Path) -> list[PostDraft]:
    return [PostDraft.from_dict(raw) for raw in json.loads(path.read_text(encoding="utf-8"))]


def save_drafts(path: Path, drafts: list[PostDraft]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([draft.to_dict() for draft in drafts], indent=2) + "\n", encoding="utf-8")


def load_schedule(path: Path) -> list[ScheduledPost]:
    return [ScheduledPost.from_dict(raw) for raw in json.loads(path.read_text(encoding="utf-8"))]


def save_schedule(path: Path, scheduled: list[ScheduledPost]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([item.to_dict() for item in scheduled], indent=2) + "\n", encoding="utf-8")


def save_receipts(path: Path, receipts: list[PostReceipt], *, append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as handle:
        for receipt in receipts:
            handle.write(json.dumps(receipt.to_dict()) + "\n")


def load_receipts(path: Path) -> list[PostReceipt]:
    if not path.exists():
        return []
    return [
        PostReceipt.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
