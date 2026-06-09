"""Build Notion page property and block payloads."""

from __future__ import annotations

import hashlib
from typing import Any

from .models import NotionSchema, ProjectRecord


def build_page_payload(
    record: ProjectRecord,
    schema: NotionSchema,
    *,
    relation_page_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
    relation_page_ids = relation_page_ids or {}
    return {
        "parent": {"data_source_id": schema.data_source_id},
        "properties": {
            "Name": {"title": [{"text": {"content": record.name}}]},
            "External ID": {"rich_text": [{"text": {"content": record.external_id}}]},
            "Status": {"select": {"name": record.status}},
            "Owner": {"rich_text": [{"text": {"content": record.owner}}]},
            "Tags": {"multi_select": [{"name": tag} for tag in record.tags]},
            "Due": {"date": {"start": record.due}},
            "URL": {"url": record.url},
            "Published": {"checkbox": record.published},
            "Related Projects": {
                "relation": [
                    {"id": relation_page_ids[external_id]}
                    for external_id in record.related_external_ids
                    if external_id in relation_page_ids
                ]
            },
        },
        "children": build_blocks(record),
    }


def build_blocks(record: ProjectRecord) -> list[dict[str, Any]]:
    blocks = [
        _paragraph(f"Summary: {record.summary}"),
        _heading("Next steps"),
    ]
    for step in record.next_steps:
        blocks.append(
            {
                "object": "block",
                "type": "to_do",
                "to_do": {"rich_text": [{"text": {"content": step}}], "checked": False},
            }
        )
    return blocks


def payload_fingerprint(payload: dict[str, Any]) -> str:
    encoded = repr(sorted(_flatten(payload))).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _paragraph(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": text}}]},
    }


def _heading(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"text": {"content": text}}]},
    }


def _flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(value, dict):
        items: list[tuple[str, str]] = []
        for key, child in value.items():
            items.extend(_flatten(child, f"{prefix}.{key}" if prefix else str(key)))
        return items
    if isinstance(value, list):
        items = []
        for index, child in enumerate(value):
            items.extend(_flatten(child, f"{prefix}[{index}]"))
        return items
    return [(prefix, repr(value))]

