"""Domain models for the social scheduler example."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import Any


NEEDS_APPROVAL = "needs_approval"
APPROVED = "approved"
POSTED = "posted"
FAILED = "failed"
TERMINAL_STATUSES = {POSTED, FAILED}


@dataclass(frozen=True)
class CampaignBrief:
    brand: str
    product: str
    audience: str
    tone: str
    campaign: str
    goals: list[str]
    features: list[str]
    call_to_action: str
    hashtags: list[str]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CampaignBrief":
        return cls(**raw)


@dataclass(frozen=True)
class PostDraft:
    id: str
    platform: str
    text: str
    campaign: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PostDraft":
        return cls(**raw)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduledPost:
    draft_id: str
    platform: str
    text: str
    campaign: str
    scheduled_at: datetime
    status: str = NEEDS_APPROVAL
    approved_by: str | None = None
    approved_at: datetime | None = None
    attempts: int = 0
    last_error: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ScheduledPost":
        return cls(
            draft_id=raw["draft_id"],
            platform=raw["platform"],
            text=raw["text"],
            campaign=raw["campaign"],
            scheduled_at=datetime.fromisoformat(raw["scheduled_at"]),
            status=raw.get("status", NEEDS_APPROVAL),
            approved_by=raw.get("approved_by"),
            approved_at=datetime.fromisoformat(raw["approved_at"]) if raw.get("approved_at") else None,
            attempts=int(raw.get("attempts", 0)),
            last_error=raw.get("last_error"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "platform": self.platform,
            "text": self.text,
            "campaign": self.campaign,
            "scheduled_at": self.scheduled_at.isoformat(),
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "attempts": self.attempts,
            "last_error": self.last_error,
        }

    def idempotency_key(self) -> str:
        return f"{self.campaign}:{self.platform}:{self.draft_id}:{self.scheduled_at.isoformat()}"

    def approve(self, *, reviewer: str, approved_at: datetime) -> "ScheduledPost":
        if self.status in TERMINAL_STATUSES:
            raise ValueError(f"Cannot approve post in {self.status} status")
        return replace(
            self,
            status=APPROVED,
            approved_by=reviewer,
            approved_at=approved_at,
            last_error=None,
        )

    def mark_posted(self) -> "ScheduledPost":
        return replace(self, status=POSTED, attempts=self.attempts + 1, last_error=None)

    def mark_failed(self, error: str) -> "ScheduledPost":
        return replace(self, status=FAILED, attempts=self.attempts + 1, last_error=error)


@dataclass(frozen=True)
class PostReceipt:
    draft_id: str
    platform: str
    posted_at: datetime
    destination: str
    status: str
    idempotency_key: str
    provider_post_id: str
    error: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PostReceipt":
        return cls(
            draft_id=raw["draft_id"],
            platform=raw["platform"],
            posted_at=datetime.fromisoformat(raw["posted_at"]),
            destination=raw["destination"],
            status=raw["status"],
            idempotency_key=raw["idempotency_key"],
            provider_post_id=raw["provider_post_id"],
            error=raw.get("error"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "platform": self.platform,
            "posted_at": self.posted_at.isoformat(),
            "destination": self.destination,
            "status": self.status,
            "idempotency_key": self.idempotency_key,
            "provider_post_id": self.provider_post_id,
            "error": self.error,
        }
