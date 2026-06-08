"""CLI for the Google Ads operations example."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .credentials import GoogleAdsCredential
from .policy import validate_plan
from .provider import MockGoogleAdsProvider
from .sqlite_store import SQLiteGoogleAdsStore
from .storage import load_conversions, load_plan
from .sync import sync_approved_mutations, upload_offline_conversions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe Google Ads operations cookbook example.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-plan")
    validate.add_argument("--plan", required=True)
    validate.add_argument("--max-daily-budget-micros", type=int, required=True)

    db_init = subparsers.add_parser("db-init")
    db_init.add_argument("--db", required=True)

    import_plan = subparsers.add_parser("import-plan")
    import_plan.add_argument("--db", required=True)
    import_plan.add_argument("--plan", required=True)
    import_plan.add_argument("--actor-id", required=True)

    approve = subparsers.add_parser("approve")
    approve.add_argument("--db", required=True)
    approve.add_argument("--mutation-id", required=True)
    approve.add_argument("--actor-id", required=True)

    sync = subparsers.add_parser("sync-approved")
    sync.add_argument("--db", required=True)
    sync.add_argument("--worker-id", required=True)
    sync.add_argument("--customer-id", required=True)
    sync.add_argument("--login-customer-id")

    upload = subparsers.add_parser("upload-conversions")
    upload.add_argument("--db", required=True)
    upload.add_argument("--conversions", required=True)
    upload.add_argument("--customer-id", required=True)
    upload.add_argument("--debug-enabled", action="store_true")

    list_mutations = subparsers.add_parser("list-mutations")
    list_mutations.add_argument("--db", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate-plan":
        plan = load_plan(Path(args.plan))
        violations = validate_plan(
            plan,
            max_daily_budget_micros=args.max_daily_budget_micros,
            allowed_domains={"northstar.example"},
        )
        for violation in violations:
            print(f"{violation.mutation_id} {violation.code} {violation.message}")
        print(f"violations={len(violations)}")
        return 0 if not violations else 1

    if args.command == "db-init":
        store = SQLiteGoogleAdsStore(Path(args.db))
        try:
            store.migrate()
        finally:
            store.close()
        print(f"migrated={args.db}")
        return 0

    if args.command == "import-plan":
        plan = load_plan(Path(args.plan))
        store = SQLiteGoogleAdsStore(Path(args.db))
        try:
            store.migrate()
            store.import_mutations(customer_id=plan.customer_id, mutations=plan.campaigns, actor_id=args.actor_id)
        finally:
            store.close()
        print(f"imported={len(plan.campaigns)} db={args.db}")
        return 0

    if args.command == "approve":
        store = SQLiteGoogleAdsStore(Path(args.db))
        try:
            store.migrate()
            store.approve(mutation_id=args.mutation_id, actor_id=args.actor_id, approved_at=datetime.now(UTC))
        finally:
            store.close()
        print(f"approved={args.mutation_id}")
        return 0

    if args.command == "sync-approved":
        store = SQLiteGoogleAdsStore(Path(args.db))
        try:
            store.migrate()
            count = sync_approved_mutations(
                store,
                credential=_credential(args.customer_id, args.login_customer_id),
                provider=MockGoogleAdsProvider(),
                now=datetime.now(UTC),
                worker_id=args.worker_id,
            )
        finally:
            store.close()
        print(f"synced={count}")
        return 0

    if args.command == "upload-conversions":
        conversions = load_conversions(Path(args.conversions))
        store = SQLiteGoogleAdsStore(Path(args.db))
        try:
            store.migrate()
            uploaded, errors = upload_offline_conversions(
                store,
                conversions=conversions,
                credential=_credential(args.customer_id, None),
                provider=MockGoogleAdsProvider(),
                now=datetime.now(UTC),
                debug_enabled=args.debug_enabled,
            )
        finally:
            store.close()
        print(f"uploaded={uploaded} errors={errors}")
        return 0

    if args.command == "list-mutations":
        store = SQLiteGoogleAdsStore(Path(args.db))
        try:
            store.migrate()
            mutations = store.list_mutations()
        finally:
            store.close()
        for mutation in mutations:
            print(f"{mutation.id} {mutation.state} {mutation.resource_name or '-'}")
        return 0

    return 2


def _credential(customer_id: str, login_customer_id: str | None) -> GoogleAdsCredential:
    return GoogleAdsCredential(
        developer_token="dev-token-demo",
        client_id="client-id-demo",
        client_secret="client-secret-demo",
        refresh_token="refresh-demo",
        access_token="access-demo",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        customer_id=customer_id,
        login_customer_id=login_customer_id,
    )


if __name__ == "__main__":
    raise SystemExit(main())
