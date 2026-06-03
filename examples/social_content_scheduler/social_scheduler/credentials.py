"""OAuth-style credential models for provider adapters.

The example stores token metadata but never contacts real social networks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class OAuthCredential:
    account_id: str
    platform: str
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: tuple[str, ...]

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now

    def refresh(self, *, now: datetime) -> "OAuthCredential":
        return OAuthCredential(
            account_id=self.account_id,
            platform=self.platform,
            access_token=f"refreshed-{self.platform}-{self.account_id}",
            refresh_token=self.refresh_token,
            expires_at=now + timedelta(hours=1),
            scopes=self.scopes,
        )

