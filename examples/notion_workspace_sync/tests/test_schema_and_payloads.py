from __future__ import annotations

import unittest
from pathlib import Path

from notion_sync.payloads import build_page_payload
from notion_sync.schema import validate_records
from notion_sync.storage import load_records, load_schema


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "data" / "projects.json"
SCHEMA = ROOT / "data" / "notion_schema.json"


class SchemaAndPayloadTests(unittest.TestCase):
    def test_records_match_schema(self) -> None:
        records = load_records(RECORDS)
        schema = load_schema(SCHEMA)

        self.assertEqual(validate_records(records, schema), [])

    def test_payload_maps_properties_and_blocks(self) -> None:
        record = load_records(RECORDS)[0]
        schema = load_schema(SCHEMA)

        payload = build_page_payload(record, schema)

        self.assertEqual(payload["parent"], {"data_source_id": "ds-projects"})
        self.assertEqual(payload["properties"]["Name"]["title"][0]["text"]["content"], record.name)
        self.assertEqual(payload["properties"]["Status"]["select"]["name"], "Active")
        self.assertEqual(len(payload["properties"]["Tags"]["multi_select"]), 3)
        self.assertEqual(len(payload["children"]), 5)

    def test_invalid_status_is_reported(self) -> None:
        records = load_records(RECORDS)
        schema = load_schema(SCHEMA)
        bad = type(records[0])(**{**records[0].to_dict(), "status": "Unknown"})

        violations = validate_records([bad, records[1]], schema)

        self.assertEqual(violations[0].code, "INVALID_STATUS")


if __name__ == "__main__":
    unittest.main()

