"""Schema validation for project records against Notion data source properties."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from .models import NotionSchema, ProjectRecord


SUPPORTED_TYPES = {
    "title",
    "rich_text",
    "select",
    "multi_select",
    "date",
    "url",
    "checkbox",
    "relation",
}


@dataclass(frozen=True)
class SchemaViolation:
    external_id: str
    code: str
    message: str


REQUIRED_PROPERTIES = {
    "Name": "title",
    "External ID": "rich_text",
    "Status": "select",
    "Owner": "rich_text",
    "Tags": "multi_select",
    "Due": "date",
    "URL": "url",
    "Published": "checkbox",
}


def validate_schema(schema: NotionSchema) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for name, expected_type in REQUIRED_PROPERTIES.items():
        actual = schema.properties.get(name)
        if actual is None:
            violations.append(SchemaViolation("-", "MISSING_PROPERTY", name))
        elif actual.type != expected_type:
            violations.append(SchemaViolation("-", "WRONG_PROPERTY_TYPE", f"{name} expected {expected_type}"))
    for name, property_schema in schema.properties.items():
        if property_schema.type not in SUPPORTED_TYPES:
            violations.append(SchemaViolation("-", "UNSUPPORTED_PROPERTY_TYPE", f"{name}:{property_schema.type}"))
    return violations


def validate_records(records: list[ProjectRecord], schema: NotionSchema) -> list[SchemaViolation]:
    violations = validate_schema(schema)
    seen: set[str] = set()
    statuses = set(schema.properties["Status"].options or [])
    tags = set(schema.properties["Tags"].options or [])
    for record in records:
        if record.external_id in seen:
            violations.append(SchemaViolation(record.external_id, "DUPLICATE_EXTERNAL_ID", record.external_id))
        seen.add(record.external_id)
        if record.status not in statuses:
            violations.append(SchemaViolation(record.external_id, "INVALID_STATUS", record.status))
        unknown_tags = sorted(set(record.tags) - tags)
        if unknown_tags:
            violations.append(SchemaViolation(record.external_id, "INVALID_TAGS", ",".join(unknown_tags)))
        try:
            date.fromisoformat(record.due)
        except ValueError:
            violations.append(SchemaViolation(record.external_id, "INVALID_DATE", record.due))
        parsed = urlparse(record.url)
        if parsed.scheme != "https" or not parsed.netloc:
            violations.append(SchemaViolation(record.external_id, "INVALID_URL", record.url))
        missing_relations = sorted(set(record.related_external_ids) - {item.external_id for item in records})
        if missing_relations:
            violations.append(SchemaViolation(record.external_id, "MISSING_RELATIONS", ",".join(missing_relations)))
    return violations

