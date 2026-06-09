"""Workers for Notion data source sync."""

from __future__ import annotations

from datetime import datetime

from .capabilities import INSERT_CONTENT, READ_CONTENT, UPDATE_CONTENT, NotionConnection
from .models import NotionSchema
from .provider import MockNotionProvider
from .sqlite_store import SQLiteNotionStore


def default_connection(data_source_id: str) -> NotionConnection:
    return NotionConnection(
        bot_id="bot-demo",
        token_label="notion-demo-token",
        capabilities={READ_CONTENT, INSERT_CONTENT, UPDATE_CONTENT},
        shared_data_source_ids={data_source_id},
    )


def sync_due_records(
    store: SQLiteNotionStore,
    *,
    schema: NotionSchema,
    provider: MockNotionProvider,
    connection: NotionConnection,
    now: datetime,
    worker_id: str,
    limit: int = 10,
) -> int:
    claimed = store.claim_pending(now=now, worker_id=worker_id, lease_seconds=300, limit=limit)
    existing_page_ids = {
        record.external_id: record.notion_page_id
        for record in store.list_records()
        if record.notion_page_id
    }
    synced = 0
    for record in claimed:
        try:
            receipt = provider.upsert_page(
                record=record,
                schema=schema,
                connection=connection,
                now=now,
                relation_page_ids=existing_page_ids,
            )
        except Exception as exc:
            store.fail(external_id=record.external_id, error=str(exc))
            continue
        if store.complete(receipt):
            synced += 1
    return synced

