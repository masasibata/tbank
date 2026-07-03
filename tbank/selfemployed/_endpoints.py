"""Пути и эндпоинты выплат самозанятым (общие для sync- и aio-клиентов)."""

from __future__ import annotations

from typing import Optional

from tbank.core.endpoint import Endpoint
from tbank.selfemployed.models import (
    CorrelationRef,
    CreateRegistryResult,
    ListRecipientsRequest,
    ListRecipientsResult,
    ListRegistriesRequest,
    ListRegistriesResult,
    PayRegistryResult,
    ReceiptsResult,
    RecipientResults,
    RegistryActionRequest,
    SubmitRegistryResult,
)

_BASE = "/api/v1/self-employed"

CREATE_RECIPIENTS_PATH = f"{_BASE}/recipients/create"
ADD_RECIPIENTS_PATH = f"{_BASE}/recipients/add/by-requisites"
CREATE_REGISTRY_PATH = f"{_BASE}/payment-registry/create"
SUBMIT_PATH = f"{_BASE}/payment-registry/submit"
PAY_PATH = f"{_BASE}/payment-registry/pay"
RECEIPTS_PATH = f"{_BASE}/payment-registry/receipts"

CREATE_RECIPIENTS_RESULT = Endpoint(
    "GET", f"{_BASE}/recipients/create/result", RecipientResults, CorrelationRef
)
ADD_RECIPIENTS_RESULT = Endpoint(
    "GET",
    f"{_BASE}/recipients/add/by-requisites/result",
    RecipientResults,
    CorrelationRef,
)
LIST_RECIPIENTS = Endpoint(
    "POST", f"{_BASE}/recipients/list", ListRecipientsResult, ListRecipientsRequest
)
CREATE_REGISTRY_RESULT = Endpoint(
    "GET",
    f"{_BASE}/payment-registry/create/result",
    CreateRegistryResult,
    CorrelationRef,
)
SUBMIT_RESULT = Endpoint(
    "GET",
    f"{_BASE}/payment-registry/submit/result",
    SubmitRegistryResult,
    CorrelationRef,
    secured=True,
)
PAY_RESULT = Endpoint(
    "POST",
    f"{_BASE}/payment-registry/pay/result",
    PayRegistryResult,
    CorrelationRef,
    secured=True,
)
RECEIPTS_RESULT = Endpoint(
    "GET",
    "/api/v2/self-employed/payment-registry/receipts/result",
    ReceiptsResult,
    CorrelationRef,
    secured=True,
)
LIST_REGISTRIES = Endpoint(
    "POST",
    f"{_BASE}/payment-registry/list",
    ListRegistriesResult,
    ListRegistriesRequest,
    secured=True,
)


def registry_path(registry_id: int) -> str:
    return f"{_BASE}/payment-registry/{registry_id}"


def registry_action(
    registry_id: int, correlation_id: Optional[str]
) -> RegistryActionRequest:
    """Тело действия над реестром: None не передаём, чтобы сохранить авто-uuid."""
    if correlation_id is None:
        return RegistryActionRequest(payment_registry_id=registry_id)
    return RegistryActionRequest(
        payment_registry_id=registry_id, correlation_id=correlation_id
    )
