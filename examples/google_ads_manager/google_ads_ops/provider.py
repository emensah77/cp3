"""Mock Google Ads provider with validate-only and partial-failure behavior."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from .credentials import GoogleAdsCredential
from .models import CampaignMutation, ConversionReceipt, MutationReceipt, OfflineConversion


@dataclass(frozen=True)
class ProviderError:
    operation_id: str
    code: str
    message: str


@dataclass(frozen=True)
class MutateResponse:
    request_id: str
    receipts: list[MutationReceipt]
    errors: list[ProviderError]


@dataclass(frozen=True)
class ConversionUploadResponse:
    request_id: str
    receipts: list[ConversionReceipt]
    errors: list[ProviderError]


class MockGoogleAdsProvider:
    def mutate_campaigns(
        self,
        mutations: list[CampaignMutation],
        *,
        credential: GoogleAdsCredential,
        validate_only: bool,
        partial_failure: bool,
        now: datetime,
    ) -> MutateResponse:
        _validate_credential(credential)
        request_id = _request_id("mutate", credential.customer_id, [item.id for item in mutations])
        receipts: list[MutationReceipt] = []
        errors: list[ProviderError] = []
        for mutation in mutations:
            if "fail" in mutation.name.lower():
                errors.append(ProviderError(mutation.id, "MOCK_POLICY_ERROR", "Mock provider rejected campaign"))
                if not partial_failure:
                    return MutateResponse(request_id, [], errors)
                continue
            if validate_only:
                continue
            resource_name = f"customers/{credential.customer_id}/campaigns/{_stable_number(mutation.id)}"
            receipts.append(
                MutationReceipt(
                    mutation_id=mutation.id,
                    customer_id=credential.customer_id,
                    resource_name=resource_name,
                    request_id=request_id,
                    idempotency_key=mutation.idempotency_key(credential.customer_id),
                    synced_at=now,
                )
            )
        return MutateResponse(request_id, receipts, errors)

    def upload_click_conversions(
        self,
        conversions: list[OfflineConversion],
        *,
        credential: GoogleAdsCredential,
        debug_enabled: bool,
        partial_failure: bool,
        now: datetime,
    ) -> ConversionUploadResponse:
        _validate_credential(credential)
        request_id = _request_id("conversion", credential.customer_id, [item.conversion_id for item in conversions])
        receipts: list[ConversionReceipt] = []
        errors: list[ProviderError] = []
        for conversion in conversions:
            error = _conversion_error(conversion, debug_enabled=debug_enabled)
            if error is not None:
                errors.append(error)
                if not partial_failure:
                    return ConversionUploadResponse(request_id, [], errors)
                continue
            receipts.append(
                ConversionReceipt(
                    conversion_id=conversion.conversion_id,
                    customer_id=credential.customer_id,
                    status="uploaded",
                    request_id=request_id,
                    idempotency_key=conversion.idempotency_key(credential.customer_id),
                    uploaded_at=now,
                )
            )
        return ConversionUploadResponse(request_id, receipts, errors)


def _validate_credential(credential: GoogleAdsCredential) -> None:
    if not credential.developer_token:
        raise RuntimeError("developer token is required")
    if not credential.access_token:
        raise RuntimeError("OAuth access token is required")


def _conversion_error(conversion: OfflineConversion, *, debug_enabled: bool) -> ProviderError | None:
    if not conversion.gclid:
        return ProviderError(conversion.conversion_id, "MISSING_GCLID", "gclid is required")
    if conversion.ad_user_data_consent != "GRANTED":
        return ProviderError(conversion.conversion_id, "CONSENT_NOT_GRANTED", "ad_user_data consent is required")
    if debug_enabled and "TEST" not in conversion.gclid:
        return ProviderError(conversion.conversion_id, "DEBUG_GCLID_NOT_RECOGNIZED", conversion.gclid)
    return None


def _request_id(prefix: str, customer_id: str, ids: list[str]) -> str:
    digest = hashlib.sha256((customer_id + ":" + ",".join(ids)).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _stable_number(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16)

