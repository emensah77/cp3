"""Domain models for rigorous Google Ads operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


PENDING_APPROVAL = "pending_approval"
APPROVED = "approved"
LEASED = "leased"
SYNCED = "synced"
FAILED = "failed"


@dataclass(frozen=True)
class CampaignMutation:
    id: str
    name: str
    channel: str
    status: str
    daily_budget_micros: int
    final_url: str
    headlines: list[str]
    descriptions: list[str]
    keywords: list[str]
    state: str = PENDING_APPROVAL
    attempts: int = 0
    resource_name: str | None = None
    last_error: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CampaignMutation":
        return cls(**raw)

    def idempotency_key(self, customer_id: str) -> str:
        return f"{customer_id}:campaign:{self.id}:{self.name}:{self.daily_budget_micros}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CampaignPlan:
    account_id: str
    customer_id: str
    campaigns: list[CampaignMutation]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CampaignPlan":
        return cls(
            account_id=raw["account_id"],
            customer_id=raw["customer_id"],
            campaigns=[CampaignMutation.from_dict(item) for item in raw["campaigns"]],
        )


@dataclass(frozen=True)
class OfflineConversion:
    conversion_id: str
    gclid: str
    conversion_action: str
    conversion_date_time: str
    conversion_value: float
    currency_code: str
    order_id: str
    ad_user_data_consent: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "OfflineConversion":
        return cls(**raw)

    def idempotency_key(self, customer_id: str) -> str:
        return f"{customer_id}:conversion:{self.conversion_id}:{self.order_id}"


@dataclass(frozen=True)
class MutationReceipt:
    mutation_id: str
    customer_id: str
    resource_name: str
    request_id: str
    idempotency_key: str
    synced_at: datetime


@dataclass(frozen=True)
class ConversionReceipt:
    conversion_id: str
    customer_id: str
    status: str
    request_id: str
    idempotency_key: str
    uploaded_at: datetime
    error: str | None = None

