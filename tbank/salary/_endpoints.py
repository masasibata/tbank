"""Пути и эндпоинты зарплатного проекта (общие для sync- и aio-клиентов)."""

from __future__ import annotations

from typing import Dict, Optional

from tbank.core.endpoint import Endpoint
from tbank.salary.models import (
    AddEmployeesResult,
    CancelResult,
    CorrelationRef,
    CreateEmployeesResult,
    CreateRegistryResult,
    CreateSubmitResult,
    ListEmployeesRequest,
    ListEmployeesResult,
    ListRegistriesRequest,
    ListRegistriesResult,
    SubmitResult,
)

_SAL = "/api/v1/salary"

ADD_EMPLOYEES_PATH = "/api/v1/employees/add/by-requisites"
CREATE_EMPLOYEES_PATH = f"{_SAL}/employees/create"
CREATE_REGISTRY_PATH = f"{_SAL}/payment-registry/create"
CREATE_SUBMIT_PATH = f"{_SAL}/payment-registry/create-submit"
SUBMIT_PATH = f"{_SAL}/payment-registry/submit"
PAY_PATH = "/api/v1/payment/payment-registry/pay"
CANCEL_PATH = f"{_SAL}/payment-registry/cancel"

ADD_EMPLOYEES_RESULT = Endpoint(
    "GET", f"{ADD_EMPLOYEES_PATH}/result", AddEmployeesResult, CorrelationRef
)
CREATE_EMPLOYEES_RESULT = Endpoint(
    "GET", f"{_SAL}/employees/create/result", CreateEmployeesResult, CorrelationRef
)
LIST_EMPLOYEES = Endpoint(
    "POST", f"{_SAL}/employees/list", ListEmployeesResult, ListEmployeesRequest
)
CREATE_REGISTRY_RESULT = Endpoint(
    "GET",
    f"{_SAL}/payment-registry/create/result",
    CreateRegistryResult,
    CorrelationRef,
)
CREATE_SUBMIT_RESULT = Endpoint(
    "GET",
    f"{_SAL}/payment-registry/create-submit/result",
    CreateSubmitResult,
    CorrelationRef,
    secured=True,
)
SUBMIT_RESULT = Endpoint(
    "GET",
    f"{_SAL}/payment-registry/submit/result",
    SubmitResult,
    CorrelationRef,
    secured=True,
)
CANCEL_RESULT = Endpoint(
    "GET",
    f"{_SAL}/payment-registry/cancel/result",
    CancelResult,
    CorrelationRef,
    secured=True,
)
LIST_REGISTRIES = Endpoint(
    "POST",
    f"{_SAL}/payment-registry/list",
    ListRegistriesResult,
    ListRegistriesRequest,
    secured=True,
)


def registry_path(registry_id: int) -> str:
    return f"{_SAL}/payment-registry/{registry_id}"


def corr_kwargs(correlation_id: Optional[str]) -> Dict[str, str]:
    """Kwargs c correlationId: пустой словарь сохраняет авто-uuid модели."""
    return {} if correlation_id is None else {"correlation_id": correlation_id}
