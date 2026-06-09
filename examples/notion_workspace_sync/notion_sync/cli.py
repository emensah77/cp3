"""CLI for the Notion workspace sync example."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from .payloads import build_page_payload
from .provider import MockNotionProvider
from .schema import validate_records
from .sqlite_store import SQLiteNotionStore
from .storage import load_records, load_schema
from .sync import default_connection, sync_due_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe Notion data source sync cookbook example.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--records", required=True)
    validate.add_argument("--schema", required=True)

    preview = subparsers.add_parser("preview")
    preview.add_argument("--records", required=True)
    preview.add_argument("--schema", required=True)

    db_init = subparsers.add_parser("db-init")
    db_init.add_argument("--db", required=True)

    import_cmd = subparsers.add_parser("import")
    import_cmd.add_argument("--db", required=True)
    import_cmd.add_argument("--records", required=True)
    import_cmd.add_argument("--schema", default="examples/notion_workspace_sync/data/notion_schema.json")

    sync_cmd = subparsers.add_parser("sync-due")
    sync_cmd.add_argument("--db", required=True)
    sync_cmd.add_argument("--schema", required=True)
    sync_cmd.add_argument("--worker-id", required=True)
    sync_cmd.add_argument("--data-source-id", required=True)

    list_cmd = subparsers.add_parser("list")
    list_cmd.add_argument("--db", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        records = load_records(Path(args.records))
        schema = load_schema(Path(args.schema))
        violations = validate_records(records, schema)
        for violation in violations:
            print(f"{violation.external_id} {violation.code} {violation.message}")
        print(f"violations={len(violations)}")
        return 0 if not violations else 1

    if args.command == "preview":
        records = load_records(Path(args.records))
        schema = load_schema(Path(args.schema))
        for record in records:
            payload = build_page_payload(record, schema)
            print(f"{record.external_id} properties={len(payload['properties'])} blocks={len(payload['children'])}")
        return 0

    if args.command == "db-init":
        store = SQLiteNotionStore(Path(args.db))
        try:
            store.migrate()
        finally:
            store.close()
        print(f"migrated={args.db}")
        return 0

    if args.command == "import":
        records = load_records(Path(args.records))
        schema = load_schema(Path(args.schema))
        store = SQLiteNotionStore(Path(args.db))
        try:
            store.migrate()
            store.import_records(records, data_source_id=schema.data_source_id, actor_id="importer")
        finally:
            store.close()
        print(f"imported={len(records)} db={args.db}")
        return 0

    if args.command == "sync-due":
        schema = load_schema(Path(args.schema))
        store = SQLiteNotionStore(Path(args.db))
        try:
            store.migrate()
            synced = sync_due_records(
                store,
                schema=schema,
                provider=MockNotionProvider(),
                connection=default_connection(args.data_source_id),
                now=datetime.now(UTC),
                worker_id=args.worker_id,
            )
        finally:
            store.close()
        print(f"synced={synced}")
        return 0

    if args.command == "list":
        store = SQLiteNotionStore(Path(args.db))
        try:
            store.migrate()
            records = store.list_records()
        finally:
            store.close()
        for record in records:
            print(f"{record.external_id} {record.state} {record.notion_page_id or '-'}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

