"""Google Ads credential metadata.

No real secrets are required for the cookbook. This mirrors the credential shape:
OAuth details, developer token, target customer, and optional manager login
customer ID.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class GoogleAdsCredential:
    developer_token: str
    client_id: str
    client_secret: str
    refresh_token: str
    access_token: str
    expires_at: datetime
    customer_id: str
    login_customer_id: str | None = None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now

    def refresh(self, *, now: datetime) -> "GoogleAdsCredential":
        return GoogleAdsCredential(
            developer_token=self.developer_token,
            client_id=self.client_id,
            client_secret=self.client_secret,
            refresh_token=self.refresh_token,
            access_token=f"refreshed-{self.customer_id}",
            expires_at=now + timedelta(hours=1),
            customer_id=self.customer_id,
            login_customer_id=self.login_customer_id,
        )

    def redacted_headers(self) -> dict[str, str]:
        headers = {
            "developer-token": _redact(self.developer_token),
            "authorization": "Bearer " + _redact(self.access_token),
            "customer-id": self.customer_id,
        }
        if self.login_customer_id:
            headers["login-customer-id"] = self.login_customer_id
        return headers


def _redact(value: str) -> str:
    if len(value) <= 6:
        return "***"
    return value[:3] + "***" + value[-3:]

