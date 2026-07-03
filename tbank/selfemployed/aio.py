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
from tbank.selfemployed import _endpoints
from tbank.selfemployed.errors import error_from_self_employed_response
from tbank.selfemployed.models import (
    AddRecipientsByRequisitesRequest,
    CorrelatedRequest,
    CorrelationRef,
    CreatePaymentRegistryRequest,
    CreateRecipientsRequest,
    CreateRegistryResult,
    ListRecipientsRequest,
    ListRecipientsResult,
    ListRegistriesRequest,
    ListRegistriesResult,
    PaymentRegistryInfo,
    PayRegistryResult,
    ReceiptsResult,
    RecipientResults,
    SubmitRegistryResult,
)


class SelfEmployedClient(BaseAsyncClient):
    """Асинхронный клиент выплат самозанятым (e2c): анкеты, платёжные реестры,
    подписание, оплата и чеки.

    Часть операций (подписание/оплата/чеки/список реестров) идёт на secured-хост
    и требует **mTLS-сертификата** (`cert`); анкеты и создание реестра — на обычном
    хосте по **Bearer**-токену. Все инициирующие методы возвращают клиентский
    `correlationId`, по которому опрашивается `*_result`.
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
        return error_from_self_employed_response(response)

    async def _initiate(
        self, path: str, body: CorrelatedRequest, *, secured: bool
    ) -> str:
        """POST-инициатор async-операции; возвращает клиентский correlationId."""
        await self._send("POST", path, body=body, secured=secured)
        return body.correlation_id

    # --- Самозанятые (получатели) ---

    async def create_recipients(self, request: CreateRecipientsRequest) -> str:
        """Создать черновики анкет самозанятых."""
        return await self._initiate(
            _endpoints.CREATE_RECIPIENTS_PATH, request, secured=False
        )

    async def get_create_recipients_result(
        self, correlation_id: str
    ) -> RecipientResults:
        """Результат создания черновиков анкет."""
        return await self._call(
            _endpoints.CREATE_RECIPIENTS_RESULT,
            CorrelationRef(correlation_id=correlation_id),
        )

    async def add_recipients_by_requisites(
        self, request: AddRecipientsByRequisitesRequest
    ) -> str:
        """Добавить самозанятых по реквизитам."""
        return await self._initiate(
            _endpoints.ADD_RECIPIENTS_PATH, request, secured=False
        )

    async def get_add_recipients_result(self, correlation_id: str) -> RecipientResults:
        """Результат добавления самозанятых по реквизитам."""
        return await self._call(
            _endpoints.ADD_RECIPIENTS_RESULT,
            CorrelationRef(correlation_id=correlation_id),
        )

    async def list_recipients(
        self, request: ListRecipientsRequest
    ) -> ListRecipientsResult:
        """Информация по самозанятым (фильтры + пагинация)."""
        return await self._call(_endpoints.LIST_RECIPIENTS, request)

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

    async def submit_payment_registry(
        self, registry_id: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Подписать платёжный реестр (mTLS)."""
        return await self._initiate(
            _endpoints.SUBMIT_PATH,
            _endpoints.registry_action(registry_id, correlation_id),
            secured=True,
        )

    async def get_submit_result(self, correlation_id: str) -> SubmitRegistryResult:
        """Результат подписания реестра (mTLS)."""
        return await self._call(
            _endpoints.SUBMIT_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def pay_payment_registry(
        self, registry_id: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Оплатить платёжный реестр (mTLS)."""
        return await self._initiate(
            _endpoints.PAY_PATH,
            _endpoints.registry_action(registry_id, correlation_id),
            secured=True,
        )

    async def get_pay_result(self, correlation_id: str) -> PayRegistryResult:
        """Результат оплаты реестра (mTLS)."""
        return await self._call(
            _endpoints.PAY_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def request_receipts(
        self, registry_id: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Запросить чеки по оплаченному реестру (mTLS)."""
        return await self._initiate(
            _endpoints.RECEIPTS_PATH,
            _endpoints.registry_action(registry_id, correlation_id),
            secured=True,
        )

    async def get_receipts_result(self, correlation_id: str) -> ReceiptsResult:
        """Результат запроса чеков — ссылки на чеки самозанятых (mTLS)."""
        return await self._call(
            _endpoints.RECEIPTS_RESULT, CorrelationRef(correlation_id=correlation_id)
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
