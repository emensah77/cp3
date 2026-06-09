"""JSON storage helpers for Notion sync."""

from __future__ import annotations

import json
from pathlib import Path

from .models import NotionSchema, ProjectRecord


def load_records(path: Path) -> list[ProjectRecord]:
    return [ProjectRecord.from_dict(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def load_schema(path: Path) -> NotionSchema:
    return NotionSchema.from_dict(json.loads(path.read_text(encoding="utf-8")))

