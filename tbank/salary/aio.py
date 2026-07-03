from __future__ import annotations

from typing import Optional

import httpx

from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import (
    AsyncTransport,
    CertTypes,
    VerifyTypes,
    build_async_transports,
)
from tbank.core.urls import (
    PROD_URL,
    SANDBOX_SECURED_URL,
    SANDBOX_URL,
    SECURED_URL,
)
from tbank.salary import _endpoints
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


class SalaryClient(BaseAsyncClient):
    """Асинхронный клиент зарплатного проекта: анкеты сотрудников, платёжные
    реестры, их создание/подписание/оплата/отмена.

    Подписание, создание-и-подписание, оплата, отмена и список реестров идут на
    secured-хост и требуют **mTLS-сертификата** (`cert`); анкеты и создание
    черновика реестра — на обычном хосте по **Bearer**-токену. Инициирующие методы
    возвращают клиентский `correlationId` (оплата — ключ идемпотентности `id`), по
    которому опрашивается `*_result`.
    """

    decimal_body = True

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        secured_base_url: Optional[str] = None,
        sandbox: bool = False,
        cert: Optional[CertTypes] = None,
        verify: VerifyTypes = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[AsyncTransport] = None,
        secured_transport: Optional[AsyncTransport] = None,
    ) -> None:
        transport, secured_transport = build_async_transports(
            token,
            base_url=base_url or (SANDBOX_URL if sandbox else PROD_URL),
            secured_base_url=secured_base_url
            or (SANDBOX_SECURED_URL if sandbox else SECURED_URL),
            cert=cert,
            verify=verify,
            retry=retry,
            transport=transport,
            secured_transport=secured_transport,
        )
        super().__init__(transport, secured_transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_salary_response(response)

    async def _initiate(
        self, path: str, body: CorrelatedRequest, *, secured: bool
    ) -> str:
        """POST-инициатор async-операции; возвращает клиентский correlationId."""
        await self._send("POST", path, body=body, secured=secured)
        return body.correlation_id

    # --- Сотрудники ---

    async def add_employees_by_requisites(
        self, request: AddEmployeesByRequisitesRequest
    ) -> str:
        """Добавить сотрудников по реквизитам."""
        return await self._initiate(
            _endpoints.ADD_EMPLOYEES_PATH, request, secured=False
        )

    async def get_add_employees_result(self, correlation_id: str) -> AddEmployeesResult:
        """Результат добавления сотрудников по реквизитам."""
        return await self._call(
            _endpoints.ADD_EMPLOYEES_RESULT,
            CorrelationRef(correlation_id=correlation_id),
        )

    async def create_employees(self, request: CreateEmployeesRequest) -> str:
        """Создать черновики анкет сотрудников."""
        return await self._initiate(
            _endpoints.CREATE_EMPLOYEES_PATH, request, secured=False
        )

    async def get_create_employees_result(
        self, correlation_id: str
    ) -> CreateEmployeesResult:
        """Результат создания черновиков анкет сотрудников."""
        return await self._call(
            _endpoints.CREATE_EMPLOYEES_RESULT,
            CorrelationRef(correlation_id=correlation_id),
        )

    async def list_employees(
        self, request: ListEmployeesRequest
    ) -> ListEmployeesResult:
        """Информация по сотрудникам по их идентификаторам."""
        return await self._call(_endpoints.LIST_EMPLOYEES, request)

    # --- Платёжный реестр ---

    async def create_payment_registry(
        self, request: CreatePaymentRegistryRequest
    ) -> str:
        """Создать черновик платёжного реестра."""
        return await self._initiate(
            _endpoints.CREATE_REGISTRY_PATH, request, secured=False
        )

    async def get_create_registry_result(
        self, correlation_id: str
    ) -> CreateRegistryResult:
        """Результат создания черновика реестра (paymentRegistryId + ошибки)."""
        return await self._call(
            _endpoints.CREATE_REGISTRY_RESULT,
            CorrelationRef(correlation_id=correlation_id),
        )

    async def create_and_submit_registry(
        self, request: CreateSubmitRegistryRequest
    ) -> str:
        """Создать и сразу подписать платёжный реестр (mTLS)."""
        return await self._initiate(
            _endpoints.CREATE_SUBMIT_PATH, request, secured=True
        )

    async def get_create_submit_result(self, correlation_id: str) -> CreateSubmitResult:
        """Результат создания-и-подписания реестра (mTLS)."""
        return await self._call(
            _endpoints.CREATE_SUBMIT_RESULT,
            CorrelationRef(correlation_id=correlation_id),
        )

    async def submit_payment_registry(
        self, registry_id: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Подписать платёжный реестр (mTLS)."""
        request = RegistryActionRequest(
            payment_registry_id=registry_id, **_endpoints.corr_kwargs(correlation_id)
        )
        return await self._initiate(_endpoints.SUBMIT_PATH, request, secured=True)

    async def get_submit_result(self, correlation_id: str) -> SubmitResult:
        """Результат подписания реестра (mTLS)."""
        return await self._call(
            _endpoints.SUBMIT_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def pay_payment_registry(self, request: PayRegistryRequest) -> str:
        """Оплатить платёжный реестр (mTLS). Возвращает ключ идемпотентности `id`."""
        await self._send("POST", _endpoints.PAY_PATH, body=request, secured=True)
        return request.id

    async def cancel_payment_registry(
        self, payment_order_number: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Отменить отправку платёжного реестра (mTLS)."""
        request = CancelRequest(
            payment_order_number=payment_order_number,
            **_endpoints.corr_kwargs(correlation_id),
        )
        return await self._initiate(_endpoints.CANCEL_PATH, request, secured=True)

    async def get_cancel_result(self, correlation_id: str) -> CancelResult:
        """Результат отмены отправки реестра (mTLS)."""
        return await self._call(
            _endpoints.CANCEL_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def list_payment_registries(
        self, request: ListRegistriesRequest
    ) -> ListRegistriesResult:
        """Список платёжных реестров за период (mTLS)."""
        return await self._call(_endpoints.LIST_REGISTRIES, request)

    async def get_payment_registry(self, registry_id: int) -> PaymentRegistryInfo:
        """Карточка платёжного реестра: суммы, статусы, платежи."""
        return await self._get(
            _endpoints.registry_path(registry_id), PaymentRegistryInfo
        )
