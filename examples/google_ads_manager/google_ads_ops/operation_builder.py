"""Compile campaign plans into concrete Google Ads resource operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import CampaignMutation, CampaignPlan


@dataclass(frozen=True)
class GoogleAdsOperation:
    operation_id: str
    mutation_id: str
    resource_type: str
    action: str
    temp_resource_name: str
    payload: dict[str, Any]
    depends_on: tuple[str, ...] = ()


def compile_plan_operations(plan: CampaignPlan) -> list[GoogleAdsOperation]:
    operations: list[GoogleAdsOperation] = []
    for campaign in plan.campaigns:
        operations.extend(compile_campaign_operations(plan.customer_id, campaign))
    return operations


def compile_campaign_operations(customer_id: str, campaign: CampaignMutation) -> list[GoogleAdsOperation]:
    budget = f"customers/{customer_id}/campaignBudgets/-{campaign.id}-budget"
    campaign_resource = f"customers/{customer_id}/campaigns/-{campaign.id}"
    ad_group = f"customers/{customer_id}/adGroups/-{campaign.id}-ag-001"
    ad = f"customers/{customer_id}/adGroupAds/-{campaign.id}-rsa-001"
    geo = f"customers/{customer_id}/campaignCriteria/-{campaign.id}-geo-us"

    operations: list[GoogleAdsOperation] = [
        GoogleAdsOperation(
            operation_id=f"{campaign.id}:budget",
            mutation_id=campaign.id,
            resource_type="CampaignBudget",
            action="create",
            temp_resource_name=budget,
            payload={
                "name": f"{campaign.name} Budget",
                "amount_micros": campaign.daily_budget_micros,
                "delivery_method": "STANDARD",
                "explicitly_shared": False,
            },
        ),
        GoogleAdsOperation(
            operation_id=f"{campaign.id}:campaign",
            mutation_id=campaign.id,
            resource_type="Campaign",
            action="create",
            temp_resource_name=campaign_resource,
            depends_on=(f"{campaign.id}:budget",),
            payload={
                "name": campaign.name,
                "status": campaign.status,
                "advertising_channel_type": campaign.channel,
                "campaign_budget": budget,
                "network_settings": {
                    "target_google_search": True,
                    "target_search_network": True,
                    "target_content_network": False,
                    "target_partner_search_network": False,
                },
            },
        ),
        GoogleAdsOperation(
            operation_id=f"{campaign.id}:ad_group",
            mutation_id=campaign.id,
            resource_type="AdGroup",
            action="create",
            temp_resource_name=ad_group,
            depends_on=(f"{campaign.id}:campaign",),
            payload={
                "name": f"{campaign.name} Core",
                "campaign": campaign_resource,
                "status": "ENABLED",
                "type": "SEARCH_STANDARD",
                "cpc_bid_micros": 2_000_000,
            },
        ),
        GoogleAdsOperation(
            operation_id=f"{campaign.id}:responsive_search_ad",
            mutation_id=campaign.id,
            resource_type="AdGroupAd",
            action="create",
            temp_resource_name=ad,
            depends_on=(f"{campaign.id}:ad_group",),
            payload={
                "ad_group": ad_group,
                "status": "PAUSED",
                "final_urls": [campaign.final_url],
                "responsive_search_ad": {
                    "headlines": [{"text": text} for text in campaign.headlines],
                    "descriptions": [{"text": text} for text in campaign.descriptions],
                },
            },
        ),
        GoogleAdsOperation(
            operation_id=f"{campaign.id}:geo_us",
            mutation_id=campaign.id,
            resource_type="CampaignCriterion",
            action="create",
            temp_resource_name=geo,
            depends_on=(f"{campaign.id}:campaign",),
            payload={
                "campaign": campaign_resource,
                "location": {"geo_target_constant": "geoTargetConstants/2840"},
                "negative": False,
            },
        ),
    ]

    for index, keyword in enumerate(campaign.keywords, start=1):
        operations.append(
            GoogleAdsOperation(
                operation_id=f"{campaign.id}:keyword:{index:03d}",
                mutation_id=campaign.id,
                resource_type="AdGroupCriterion",
                action="create",
                temp_resource_name=f"customers/{customer_id}/adGroupCriteria/-{campaign.id}-kw-{index:03d}",
                depends_on=(f"{campaign.id}:ad_group",),
                payload={
                    "ad_group": ad_group,
                    "status": "ENABLED",
                    "keyword": {
                        "text": keyword,
                        "match_type": "PHRASE",
                    },
                },
            )
        )

    return operations


def summarize_operations(operations: list[GoogleAdsOperation]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for operation in operations:
        counts[operation.resource_type] = counts.get(operation.resource_type, 0) + 1
    return counts

