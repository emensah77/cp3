from __future__ import annotations

import unittest
from pathlib import Path

from google_ads_ops.operation_builder import compile_plan_operations, summarize_operations
from google_ads_ops.provider import validate_operation_graph
from google_ads_ops.storage import load_plan


PLAN = Path(__file__).resolve().parents[1] / "data" / "campaign_plan.json"


class OperationBuilderTests(unittest.TestCase):
    def test_compile_plan_creates_concrete_google_ads_resources(self) -> None:
        plan = load_plan(PLAN)

        operations = compile_plan_operations(plan)
        summary = summarize_operations(operations)

        self.assertEqual(summary["CampaignBudget"], 2)
        self.assertEqual(summary["Campaign"], 2)
        self.assertEqual(summary["AdGroup"], 2)
        self.assertEqual(summary["AdGroupAd"], 2)
        self.assertEqual(summary["AdGroupCriterion"], 6)
        self.assertEqual(summary["CampaignCriterion"], 2)
        self.assertEqual(len(operations), 16)

    def test_operation_graph_dependencies_are_ordered(self) -> None:
        plan = load_plan(PLAN)

        errors = validate_operation_graph(compile_plan_operations(plan)[:7])

        self.assertEqual(errors, [])

    def test_operation_payload_contains_responsive_search_ad_assets(self) -> None:
        plan = load_plan(PLAN)
        operations = compile_plan_operations(plan)

        rsa = next(operation for operation in operations if operation.resource_type == "AdGroupAd")

        self.assertEqual(rsa.payload["status"], "PAUSED")
        self.assertEqual(len(rsa.payload["responsive_search_ad"]["headlines"]), 3)
        self.assertEqual(len(rsa.payload["responsive_search_ad"]["descriptions"]), 2)
        self.assertEqual(rsa.payload["final_urls"], ["https://northstar.example/signup"])


if __name__ == "__main__":
    unittest.main()
