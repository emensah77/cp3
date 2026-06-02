"""Posting providers for the social scheduler example."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .models import ScheduledPost


@dataclass(frozen=True)
class ProviderResult:
    provider_post_id: str


class MockSocialProvider:
    """Deterministic provider used for tests and cookbook safety."""

    def __init__(self, *, fail_platforms: set[str] | None = None) -> None:
        self.fail_platforms = fail_platforms or set()

    def publish(self, item: ScheduledPost, *, idempotency_key: str) -> ProviderResult:
        if item.platform in self.fail_platforms:
            raise RuntimeError(f"mock provider rejected platform: {item.platform}")
        digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:10]
        return ProviderResult(provider_post_id=f"mock-{item.platform}-{digest}")
