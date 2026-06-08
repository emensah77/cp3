from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from google_ads_ops.credentials import GoogleAdsCredential
from google_ads_ops.models import CampaignMutation, OfflineConversion
from google_ads_ops.policy import validate_plan
from google_ads_ops.provider import MockGoogleAdsProvider
from google_ads_ops.storage import load_plan


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "campaign_plan.json"


def credential() -> GoogleAdsCredential:
    return GoogleAdsCredential(
        developer_token="developer-token-demo",
        client_id="client",
        client_secret="secret",
        refresh_token="refresh",
        access_token="access-token-demo",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        customer_id="1234567890",
        login_customer_id="9998887777",
    )


class PolicyAndProviderTests(unittest.TestCase):
    def test_valid_plan_has_no_policy_violations(self) -> None:
        plan = load_plan(PLAN)

        violations = validate_plan(
            plan,
            max_daily_budget_micros=50_000_000,
            allowed_domains={"northstar.example"},
        )

        self.assertEqual(violations, [])

    def test_policy_blocks_budget_and_domain_violations(self) -> None:
        plan = load_plan(PLAN)
        bad = CampaignMutation(
            **{**plan.campaigns[0].to_dict(), "daily_budget_micros": 99_000_000, "final_url": "http://bad.example"}
        )
        plan = type(plan)(account_id=plan.account_id, customer_id=plan.customer_id, campaigns=[bad])

        violations = validate_plan(plan, max_daily_budget_micros=50_000_000, allowed_domains={"northstar.example"})

        self.assertEqual(
            sorted(item.code for item in violations),
            ["BUDGET_TOO_HIGH", "DOMAIN_NOT_ALLOWED", "INSECURE_FINAL_URL"],
        )

    def test_credentials_redact_sensitive_headers(self) -> None:
        headers = credential().redacted_headers()

        self.assertEqual(headers["developer-token"], "dev***emo")
        self.assertEqual(headers["authorization"], "Bearer acc***emo")
        self.assertEqual(headers["login-customer-id"], "9998887777")

    def test_mutate_validate_only_returns_no_receipts(self) -> None:
        plan = load_plan(PLAN)

        response = MockGoogleAdsProvider().mutate_campaigns(
            plan.campaigns,
            credential=credential(),
            validate_only=True,
            partial_failure=True,
            now=datetime(2026, 6, 8, 12),
        )

        self.assertEqual(response.receipts, [])
        self.assertEqual(response.errors, [])

    def test_mutate_partial_failure_keeps_successes(self) -> None:
        plan = load_plan(PLAN)
        failing = CampaignMutation(**{**plan.campaigns[0].to_dict(), "id": "mut-fail", "name": "Fail Campaign"})

        response = MockGoogleAdsProvider().mutate_campaigns(
            [plan.campaigns[0], failing],
            credential=credential(),
            validate_only=False,
            partial_failure=True,
            now=datetime(2026, 6, 8, 12),
        )

        self.assertEqual([receipt.mutation_id for receipt in response.receipts], ["mut-001"])
        self.assertEqual(response.errors[0].operation_id, "mut-fail")

    def test_conversion_upload_returns_debug_errors(self) -> None:
        conversions = [
            OfflineConversion(
                conversion_id="conv-bad",
                gclid="",
                conversion_action="customers/1234567890/conversionActions/111",
                conversion_date_time="2026-06-08T10:15:00-07:00",
                conversion_value=10.0,
                currency_code="USD",
                order_id="order-bad",
                ad_user_data_consent="GRANTED",
            )
        ]

        response = MockGoogleAdsProvider().upload_click_conversions(
            conversions,
            credential=credential(),
            debug_enabled=True,
            partial_failure=True,
            now=datetime(2026, 6, 8, 12),
        )

        self.assertEqual(response.receipts, [])
        self.assertEqual(response.errors[0].code, "MISSING_GCLID")


if __name__ == "__main__":
    unittest.main()
