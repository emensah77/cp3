"""Domain models for Notion workspace sync."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


PENDING = "pending"
LEASED = "leased"
SYNCED = "synced"
FAILED = "failed"


@dataclass(frozen=True)
class ProjectRecord:
    external_id: str
    name: str
    status: str
    owner: str
    tags: list[str]
    due: str
    url: str
    published: bool
    related_external_ids: list[str]
    summary: str
    next_steps: list[str]
    state: str = PENDING
    attempts: int = 0
    notion_page_id: str | None = None
    last_error: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProjectRecord":
        return cls(**raw)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def idempotency_key(self, data_source_id: str) -> str:
        return f"{data_source_id}:project:{self.external_id}"


@dataclass(frozen=True)
class PropertySchema:
    type: str
    options: list[str] | None = None
    data_source_id: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PropertySchema":
        return cls(
            type=raw["type"],
            options=raw.get("options"),
            data_source_id=raw.get("data_source_id"),
        )


@dataclass(frozen=True)
class NotionSchema:
    data_source_id: str
    title_property: str
    properties: dict[str, PropertySchema]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "NotionSchema":
        return cls(
            data_source_id=raw["data_source_id"],
            title_property=raw["title_property"],
            properties={name: PropertySchema.from_dict(value) for name, value in raw["properties"].items()},
        )


@dataclass(frozen=True)
class SyncReceipt:
    external_id: str
    data_source_id: str
    notion_page_id: str
    request_id: str
    idempotency_key: str
    synced_at: datetime

