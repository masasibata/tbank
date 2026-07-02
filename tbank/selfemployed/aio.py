from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.endpoint import Endpoint
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport
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
    RegistryActionRequest,
    SubmitRegistryResult,
)

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"
SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_BASE = "/api/v1/self-employed"
_P_CREATE_RECIPIENTS = f"{_BASE}/recipients/create"
_P_ADD_RECIPIENTS = f"{_BASE}/recipients/add/by-requisites"
_P_CREATE_REGISTRY = f"{_BASE}/payment-registry/create"
_P_SUBMIT = f"{_BASE}/payment-registry/submit"
_P_PAY = f"{_BASE}/payment-registry/pay"
_P_RECEIPTS = f"{_BASE}/payment-registry/receipts"

_CREATE_RECIPIENTS_RESULT = Endpoint(
    "GET", f"{_BASE}/recipients/create/result", RecipientResults, CorrelationRef
)
_ADD_RECIPIENTS_RESULT = Endpoint(
    "GET",
    f"{_BASE}/recipients/add/by-requisites/result",
    RecipientResults,
    CorrelationRef,
)
_LIST_RECIPIENTS = Endpoint(
    "POST", f"{_BASE}/recipients/list", ListRecipientsResult, ListRecipientsRequest
)
_CREATE_REGISTRY_RESULT = Endpoint(
    "GET",
    f"{_BASE}/payment-registry/create/result",
    CreateRegistryResult,
    CorrelationRef,
)
_SUBMIT_RESULT = Endpoint(
    "GET",
    f"{_BASE}/payment-registry/submit/result",
    SubmitRegistryResult,
    CorrelationRef,
    secured=True,
)
_PAY_RESULT = Endpoint(
    "POST",
    f"{_BASE}/payment-registry/pay/result",
    PayRegistryResult,
    CorrelationRef,
    secured=True,
)
_RECEIPTS_RESULT = Endpoint(
    "GET",
    "/api/v2/self-employed/payment-registry/receipts/result",
    ReceiptsResult,
    CorrelationRef,
    secured=True,
)
_LIST_REGISTRIES = Endpoint(
    "POST",
    f"{_BASE}/payment-registry/list",
    ListRegistriesResult,
    ListRegistriesRequest,
    secured=True,
)


class SelfEmployedClient(BaseAsyncClient):
    """Асинхронный клиент выплат самозанятым (e2c): анкеты, платёжные реестры,
    подписание, оплата и чеки.

    Часть операций (подписание/оплата/чеки/список реестров) идёт на secured-хост
    и требует **mTLS-сертификата** (`cert`); анкеты и создание реестра — на обычном
    хосте по **Bearer**-токену. Все инициирующие методы возвращают клиентский
    `correlationId`, по которому опрашивается `*_result`.
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
        return error_from_self_employed_response(response)

    async def _initiate(
        self, path: str, body: CorrelatedRequest, *, secured: bool
    ) -> str:
        """POST-инициатор async-операции; возвращает клиентский correlationId."""
        transport = self._pick_transport(secured)
        payload = body.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = await transport.request("POST", path, json=payload)
        self._raise_for_http(response)
        return body.correlation_id

    # --- Самозанятые (получатели) ---

    async def create_recipients(self, request: CreateRecipientsRequest) -> str:
        """Создать черновики анкет самозанятых."""
        return await self._initiate(_P_CREATE_RECIPIENTS, request, secured=False)

    async def get_create_recipients_result(
        self, correlation_id: str
    ) -> RecipientResults:
        """Результат создания черновиков анкет."""
        return await self._call(
            _CREATE_RECIPIENTS_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def add_recipients_by_requisites(
        self, request: AddRecipientsByRequisitesRequest
    ) -> str:
        """Добавить самозанятых по реквизитам."""
        return await self._initiate(_P_ADD_RECIPIENTS, request, secured=False)

    async def get_add_recipients_result(self, correlation_id: str) -> RecipientResults:
        """Результат добавления самозанятых по реквизитам."""
        return await self._call(
            _ADD_RECIPIENTS_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def list_recipients(
        self, request: ListRecipientsRequest
    ) -> ListRecipientsResult:
        """Информация по самозанятым (фильтры + пагинация)."""
        return await self._call(_LIST_RECIPIENTS, request)

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

    async def submit_payment_registry(
        self, registry_id: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Подписать платёжный реестр (mTLS)."""
        return await self._initiate(
            _P_SUBMIT, self._action(registry_id, correlation_id), secured=True
        )

    async def get_submit_result(self, correlation_id: str) -> SubmitRegistryResult:
        """Результат подписания реестра (mTLS)."""
        return await self._call(
            _SUBMIT_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def pay_payment_registry(
        self, registry_id: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Оплатить платёжный реестр (mTLS)."""
        return await self._initiate(
            _P_PAY, self._action(registry_id, correlation_id), secured=True
        )

    async def get_pay_result(self, correlation_id: str) -> PayRegistryResult:
        """Результат оплаты реестра (mTLS)."""
        return await self._call(
            _PAY_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def request_receipts(
        self, registry_id: int, *, correlation_id: Optional[str] = None
    ) -> str:
        """Запросить чеки по оплаченному реестру (mTLS)."""
        return await self._initiate(
            _P_RECEIPTS, self._action(registry_id, correlation_id), secured=True
        )

    async def get_receipts_result(self, correlation_id: str) -> ReceiptsResult:
        """Результат запроса чеков — ссылки на чеки самозанятых (mTLS)."""
        return await self._call(
            _RECEIPTS_RESULT, CorrelationRef(correlation_id=correlation_id)
        )

    async def list_payment_registries(
        self, request: ListRegistriesRequest
    ) -> ListRegistriesResult:
        """Список платёжных реестров за период (mTLS)."""
        return await self._call(_LIST_REGISTRIES, request)

    async def get_payment_registry(self, registry_id: int) -> PaymentRegistryInfo:
        """Карточка платёжного реестра: суммы, статусы, платежи."""
        response = await self._transport.request(
            "GET", f"{_BASE}/payment-registry/{registry_id}"
        )
        self._raise_for_http(response)
        return PaymentRegistryInfo.model_validate(self._parse_body(response))

    @staticmethod
    def _action(
        registry_id: int, correlation_id: Optional[str]
    ) -> RegistryActionRequest:
        if correlation_id is None:
            return RegistryActionRequest(payment_registry_id=registry_id)
        return RegistryActionRequest(
            payment_registry_id=registry_id, correlation_id=correlation_id
        )
