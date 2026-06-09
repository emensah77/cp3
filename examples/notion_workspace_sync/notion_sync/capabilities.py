"""Connection capability checks for the Notion example."""

from __future__ import annotations

from dataclasses import dataclass


READ_CONTENT = "read_content"
INSERT_CONTENT = "insert_content"
UPDATE_CONTENT = "update_content"


@dataclass(frozen=True)
class NotionConnection:
    bot_id: str
    token_label: str
    capabilities: set[str]
    shared_data_source_ids: set[str]

    def can_access(self, data_source_id: str) -> bool:
        return data_source_id in self.shared_data_source_ids


def require_capability(connection: NotionConnection, capability: str) -> None:
    if capability not in connection.capabilities:
        raise PermissionError(f"Connection {connection.bot_id} lacks {capability}")


def require_data_source_access(connection: NotionConnection, data_source_id: str) -> None:
    if not connection.can_access(data_source_id):
        raise PermissionError(f"Connection {connection.bot_id} cannot access data source {data_source_id}")

