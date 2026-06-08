"""Budget and policy validation for campaign plans."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .models import CampaignMutation, CampaignPlan


PROHIBITED_TERMS = {"guaranteed cure", "instant wealth", "miracle"}
ALLOWED_CHANNELS = {"SEARCH", "DISPLAY", "PERFORMANCE_MAX"}


@dataclass(frozen=True)
class PolicyViolation:
    mutation_id: str
    code: str
    message: str


def validate_plan(
    plan: CampaignPlan,
    *,
    max_daily_budget_micros: int,
    allowed_domains: set[str] | None = None,
) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    seen_ids: set[str] = set()
    for campaign in plan.campaigns:
        violations.extend(_validate_campaign(campaign, max_daily_budget_micros=max_daily_budget_micros))
        if campaign.id in seen_ids:
            violations.append(PolicyViolation(campaign.id, "DUPLICATE_ID", "Mutation ids must be unique"))
        seen_ids.add(campaign.id)
        if allowed_domains is not None:
            host = urlparse(campaign.final_url).hostname or ""
            if host not in allowed_domains:
                violations.append(PolicyViolation(campaign.id, "DOMAIN_NOT_ALLOWED", host))
    return violations


def _validate_campaign(campaign: CampaignMutation, *, max_daily_budget_micros: int) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    if campaign.channel not in ALLOWED_CHANNELS:
        violations.append(PolicyViolation(campaign.id, "INVALID_CHANNEL", campaign.channel))
    if campaign.daily_budget_micros <= 0:
        violations.append(PolicyViolation(campaign.id, "INVALID_BUDGET", "Budget must be positive"))
    if campaign.daily_budget_micros > max_daily_budget_micros:
        violations.append(PolicyViolation(campaign.id, "BUDGET_TOO_HIGH", str(campaign.daily_budget_micros)))
    if len(campaign.headlines) < 3:
        violations.append(PolicyViolation(campaign.id, "TOO_FEW_HEADLINES", "At least 3 headlines required"))
    if len(campaign.descriptions) < 2:
        violations.append(PolicyViolation(campaign.id, "TOO_FEW_DESCRIPTIONS", "At least 2 descriptions required"))
    text = " ".join([campaign.name, *campaign.headlines, *campaign.descriptions]).lower()
    for term in PROHIBITED_TERMS:
        if term in text:
            violations.append(PolicyViolation(campaign.id, "PROHIBITED_TERM", term))
    if not campaign.final_url.startswith("https://"):
        violations.append(PolicyViolation(campaign.id, "INSECURE_FINAL_URL", campaign.final_url))
    return violations

