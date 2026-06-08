"""JSON storage helpers for Google Ads operations."""

from __future__ import annotations

import json
from pathlib import Path

from .models import CampaignPlan, OfflineConversion


def load_plan(path: Path) -> CampaignPlan:
    return CampaignPlan.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_conversions(path: Path) -> list[OfflineConversion]:
    return [OfflineConversion.from_dict(item) for item in json.loads(path.read_text(encoding="utf-8"))]

