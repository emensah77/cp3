"""Posting providers for the social scheduler example."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from .credentials import OAuthCredential
from .models import ScheduledPost


@dataclass(frozen=True)
class ProviderResult:
    provider_post_id: str
    canonical_url: str | None = None


class SocialProvider(Protocol):
    def publish(
        self,
        item: ScheduledPost,
        *,
        idempotency_key: str,
        credential: OAuthCredential | None = None,
    ) -> ProviderResult:
        ...


class MockSocialProvider:
    """Deterministic provider used for tests and cookbook safety."""

    def __init__(self, *, fail_platforms: set[str] | None = None) -> None:
        self.fail_platforms = fail_platforms or set()

    def publish(
        self,
        item: ScheduledPost,
        *,
        idempotency_key: str,
        credential: OAuthCredential | None = None,
    ) -> ProviderResult:
        if item.platform in self.fail_platforms:
            raise RuntimeError(f"mock provider rejected platform: {item.platform}")
        if credential is not None and item.platform != credential.platform:
            raise RuntimeError("credential platform does not match scheduled post")
        digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:10]
        provider_post_id = f"mock-{item.platform}-{digest}"
        return ProviderResult(
            provider_post_id=provider_post_id,
            canonical_url=f"https://mock.social/{item.platform}/{provider_post_id}",
        )


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, SocialProvider] = {}

    def register(self, platform: str, provider: SocialProvider) -> None:
        self._providers[platform] = provider

    def get(self, platform: str) -> SocialProvider:
        try:
            return self._providers[platform]
        except KeyError as exc:
            raise ValueError(f"No provider registered for platform: {platform}") from exc
