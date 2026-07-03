from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.endpoint import Endpoint
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport
from tbank.salary.errors import error_from_salary_response
from tbank.salary.models import (
    AddEmployeesByRequisitesRequest,
    AddEmployeesResult,
    CancelRequest,
    CancelResult,
    CorrelatedRequest,
    CorrelationRef,
    CreateEmployeesRequest,
    CreateEmployeesResult,
    CreatePaymentRegistryRequest,
    CreateRegistryResult,
    CreateSubmitRegistryRequest,
    CreateSubmitResult,
    ListEmployeesRequest,
    ListEmployeesResult,
    ListRegistriesRequest,
    ListRegistriesResult,
    PaymentRegistryInfo,
    PayRegistryRequest,
    RegistryActionRequest,
    SubmitResult,
)

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"
SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_SAL = "/api/v1/salary"
_P_ADD_EMPLOYEES = "/api/v1/employees/add/by-requisites"
_P_CREATE_EMPLOYEES = f"{_SAL}/employees/create"
_P_CREATE_REGISTRY = f"{_SAL}/payment-registry/create"
_P_CREATE_SUBMIT = f"{_SAL}/payment-registry/create-submit"
_P_SUBMIT = f"{_SAL}/payment-registry/submit"
_P_PAY = "/api/v1/payment/payment-registry/pay"
_P_CANCEL = f"{_SAL}/payment-registry/cancel"

_ADD_EMPLOYEES_RESULT = Endpoint(
    "GET", f"{_P_ADD_EMPLOYEES}/result", AddEmployeesResult, CorrelationRef
)
_CREATE_EMPLOYEES_RESULT = Endpoint(
    "GET", f"{_SAL}/employees/create/result", CreateEmployeesResult, CorrelationRef
)
_LIST_EMPLOYEES = Endpoint(
    "POST", f"{_SAL}/employees/list", ListEmployeesResult, ListEmployeesRequest
)
_CREATE_REGISTRY_RESULT = Endpoint(
    "GET",
    f"{_SAL}/payment-registry/create/result",
    CreateRegistryResult,
    CorrelationRef,
)
_CREATE_SUBMIT_RESULT = Endpoint(
    "GET",
    f"{_SAL}/payment-registry/create-submit/result",
    CreateSubmitResult,
    CorrelationRef,
    secured=True,
)
_SUBMIT_RESULT = Endpoint(
    "GET",
    f"{_SAL}/payment-registry/submit/result",
    SubmitResult,
    CorrelationRef,
    secured=True,
)
_CANCEL_RESULT = Endpoint(
    "GET",
    f"{_SAL}/payment-registry/cancel/result",
    CancelResult,
    CorrelationRef,
    secured=True,
)
_LIST_REGISTRIES = Endpoint(
    "POST",
    f"{_SAL}/payment-registry/list",
    ListRegistriesResult,
    ListRegistriesRequest,
    secured=True,
)


class SalaryClient(BaseAsyncClient):
    """Асинхронный клиент зарплатного проекта: анкеты сотрудников, платёжные
    реестры, их создание/подписание/оплата/отмена.

    Подписание, создание-и-подписание, оплата, отмена и список реестров идут на
    secured-хост и требуют **mTLS-сертификата** (`cert`); анкеты и создание
    черновика реестра — на обычном хосте по **Bearer**-токену. Инициирующие методы
    возвращают клиентский `correlationId` (оплата — ключ идемпотентности `id`), по
    которому опрашивается `*_result`.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        secured_base_url: Optional[str] = None,
        sandbox: bool = False,
        cert: Optional[Any] = None,
        verify: Any = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[AsyncTransport] = None,
        secured_transport: Optional[AsyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_URL if sandbox else PROD_URL)
        transport = transport or AsyncTransport(
            base_url=resolved, auth=BearerAuth(token), retry=retry
        )
        if secured_transport is None and cert is not None:
            secured_resolved = secured_base_url or (
                SANDBOX_SECURED_URL if sandbox else SECURED_URL
            )
            secured_transport = AsyncTransport(
                base_url=secured_resolved,
                auth=BearerAuth(token),
                retry=retry,
                cert=cert,
                verify=verify,
            )
        super().__init__(transport, secured_transport)

    def _parse_body(self, response: httpx.Response) -> Any:
        # parse_float=Decimal — точные суммы выплат без float-погрешности.
        return json.loads(response.text or "null", parse_float=Decimal)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_salary_response(response)

    async def _initiate(
        self, path: str, body: CorrelatedRequest, *, secured: bool
    ) -> str:
        """POST-инициатор async-операции; возвращает клиентский correlationId."""
        transport = self._pick_transport(secured)
        payload = body.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = await transport.request("POST", path, json=payload)
        self._raise_for_http(response)
        return body.correlation_id

    # --- Сотрудники ---

    async def add_employees_by_requisites(
        self, request: AddEmployeesByRequisitesRequest
    ) -> str:
        """Добавить сотрудников по реквизитам."""
        return await self._initiate(_P_ADD_EMPLOYEES, request, secured=False)

    async def get_add_employees_result(self, correlation_id: str) -> AddEmployeesResult:
        """Результат добавления сотрудников по реквизитам."""
        return await self._call(
            _ADD_EMPLOYEES_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def create_employees(self, request: CreateEmployeesRequest) -> str:
        """Создать черновики анкет сотрудников."""
        return await self._initiate(_P_CREATE_EMPLOYEES, request, secured=False)

    async def get_create_employees_result(
        self, correlation_id: str
    ) -> CreateEmployeesResult:
        """Результат создания черновиков анкет сотрудников."""
        return await self._call(
            _CREATE_EMPLOYEES_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def list_employees(
        self, request: ListEmployeesRequest
    ) -> ListEmployeesResult:
        """Информация по сотрудникам по их идентификаторам."""
        return await self._call(_LIST_EMPLOYEES, request)

    # --- Платёжный реестр ---

    async def create_payment_registry(
        self, request: CreatePaymentRegistryRequest
    ) -> str:
        """Создать черновик платёжного реестра."""
        return await self._initiate(_P_CREATE_REGISTRY, request, secured=False)

    async def get_create_registry_result(
        self, correlation_id: str
    ) -> CreateRegistryResult:
        """Результат создания черновика реестра (paymentRegistryId + ошибки)."""
        return await self._call(
            _CREATE_REGISTRY_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def create_and_submit_registry(
        self, request: CreateSubmitRegistryRequest
    ) -> str:
        """Создать и сразу подписать платёжный реестр (mTLS)."""
        return await self._initiate(_P_CREATE_SUBMIT, request, secured=True)

    async def get_create_submit_result(self, correlation_id: str) -> CreateSubmitResult:
        """Результат создания-и-подписания реестра (mTLS)."""
        return await self._call(
            _CREATE_SUBMIT_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def submit_payment_registry(
        self, registry_id: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Подписать платёжный реестр (mTLS)."""
        request = RegistryActionRequest(
            payment_registry_id=registry_id, **_corr(correlation_id)
        )
        return await self._initiate(_P_SUBMIT, request, secured=True)

    async def get_submit_result(self, correlation_id: str) -> SubmitResult:
        """Результат подписания реестра (mTLS)."""
        return await self._call(
            _SUBMIT_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def pay_payment_registry(self, request: PayRegistryRequest) -> str:
        """Оплатить платёжный реестр (mTLS). Возвращает ключ идемпотентности `id`."""
        transport = self._pick_transport(secured=True)
        payload = request.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = await transport.request("POST", _P_PAY, json=payload)
        self._raise_for_http(response)
        return request.id

    async def cancel_payment_registry(
        self, payment_order_number: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Отменить отправку платёжного реестра (mTLS)."""
        request = CancelRequest(
            payment_order_number=payment_order_number, **_corr(correlation_id)
        )
        return await self._initiate(_P_CANCEL, request, secured=True)

    async def get_cancel_result(self, correlation_id: str) -> CancelResult:
        """Результат отмены отправки реестра (mTLS)."""
        return await self._call(
            _CANCEL_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def list_payment_registries(
        self, request: ListRegistriesRequest
    ) -> ListRegistriesResult:
        """Список платёжных реестров за период (mTLS)."""
        return await self._call(_LIST_REGISTRIES, request)

    async def get_payment_registry(self, registry_id: int) -> PaymentRegistryInfo:
        """Карточка платёжного реестра: суммы, статусы, платежи."""
        response = await self._transport.request(
            "GET", f"{_SAL}/payment-registry/{registry_id}"
        )
        self._raise_for_http(response)
        return PaymentRegistryInfo.model_validate(self._parse_body(response))


def _corr(correlation_id: Optional[str]) -> Dict[str, str]:
    return {} if correlation_id is None else {"correlation_id": correlation_id}
