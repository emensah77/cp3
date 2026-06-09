"""Mock Notion provider with create/update/query semantics."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .capabilities import INSERT_CONTENT, UPDATE_CONTENT, NotionConnection, require_capability, require_data_source_access
from .models import NotionSchema, ProjectRecord, SyncReceipt
from .payloads import build_page_payload, payload_fingerprint


@dataclass(frozen=True)
class ProviderPage:
    page_id: str
    external_id: str
    fingerprint: str
    payload: dict[str, Any]


class MockNotionProvider:
    def __init__(self) -> None:
        self.pages_by_external_id: dict[str, ProviderPage] = {}

    def upsert_page(
        self,
        *,
        record: ProjectRecord,
        schema: NotionSchema,
        connection: NotionConnection,
        now: datetime,
        relation_page_ids: dict[str, str] | None = None,
    ) -> SyncReceipt:
        require_data_source_access(connection, schema.data_source_id)
        payload = build_page_payload(record, schema, relation_page_ids=relation_page_ids)
        fingerprint = payload_fingerprint(payload)
        existing = self.pages_by_external_id.get(record.external_id)
        if existing is None:
            require_capability(connection, INSERT_CONTENT)
            page_id = _page_id(schema.data_source_id, record.external_id)
        else:
            require_capability(connection, UPDATE_CONTENT)
            page_id = existing.page_id
        self.pages_by_external_id[record.external_id] = ProviderPage(
            page_id=page_id,
            external_id=record.external_id,
            fingerprint=fingerprint,
            payload=payload,
        )
        return SyncReceipt(
            external_id=record.external_id,
            data_source_id=schema.data_source_id,
            notion_page_id=page_id,
            request_id=_request_id(schema.data_source_id, record.external_id, fingerprint),
            idempotency_key=record.idempotency_key(schema.data_source_id),
            synced_at=now,
        )

    def query_by_external_id(self, external_id: str) -> ProviderPage | None:
        return self.pages_by_external_id.get(external_id)


def _page_id(data_source_id: str, external_id: str) -> str:
    digest = hashlib.sha256(f"{data_source_id}:{external_id}".encode("utf-8")).hexdigest()[:12]
    return f"page-{digest}"


def _request_id(data_source_id: str, external_id: str, fingerprint: str) -> str:
    digest = hashlib.sha256(f"{data_source_id}:{external_id}:{fingerprint}".encode("utf-8")).hexdigest()[:12]
    return f"notion-{digest}"

