from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, AsyncIterator, List, Optional

import httpx
from pydantic import TypeAdapter

from tbank.business.errors import error_from_business_response
from tbank.business.models import (
    Account,
    BankStatement,
    BankStatementParams,
    CreateOnetimeQrRequest,
    CreatePaymentRequest,
    CreateReusableQrRequest,
    DocumentsStatusRequest,
    DocumentsStatusResponse,
    InvoiceInfo,
    PaymentStatusResponse,
    SbpQrResponse,
    SendInvoiceRequest,
    SendInvoiceResponse,
    StatementOperation,
    StatementPage,
    StatementParams,
)
from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.endpoint import Endpoint
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"
SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_ACCOUNTS_PATH = "/api/v2/bank-accounts"
_RUBLE_TRANSFER_PATH = "/api/v1/payment/ruble-transfer/pay"
_STATEMENT = Endpoint("GET", "/api/v1/statement", StatementPage, StatementParams)
_BANK_STATEMENT = Endpoint(
    "GET", "/api/v1/bank-statement", BankStatement, BankStatementParams
)
_DOCUMENTS_STATUS = Endpoint(
    "POST", "/api/v1/payment/status", DocumentsStatusResponse, DocumentsStatusRequest
)
_INVOICE_SEND = Endpoint(
    "POST", "/api/v1/invoice/send", SendInvoiceResponse, SendInvoiceRequest
)
_QR_ONETIME = Endpoint(
    "POST", "/api/v1/b2b/qr/onetime", SbpQrResponse, CreateOnetimeQrRequest
)
_QR_REUSABLE = Endpoint(
    "POST", "/api/v1/b2b/qr/reusable", SbpQrResponse, CreateReusableQrRequest
)
_ACCOUNTS_ADAPTER = TypeAdapter(List[Account])


class BusinessClient(BaseAsyncClient):
    """Асинхронный клиент T-API (открытый банк Т-Бизнес): счета и выписки."""

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
        # parse_float=Decimal — точные денежные суммы без float-погрешности.
        return json.loads(response.text or "null", parse_float=Decimal)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_business_response(response)

    async def get_accounts(self) -> List[Account]:
        """Список счетов с балансами."""
        response = await self._transport.request("GET", _ACCOUNTS_PATH)
        self._raise_for_http(response)
        return _ACCOUNTS_ADAPTER.validate_python(self._parse_body(response))

    async def get_statement(self, params: StatementParams) -> StatementPage:
        """Одна страница выписки операций (курсорная пагинация)."""
        return await self._call(_STATEMENT, params)

    async def iter_statement(
        self, params: StatementParams
    ) -> AsyncIterator[StatementOperation]:
        """Все операции выписки: автоматически следует за nextCursor."""
        cursor = params.cursor
        while True:
            page = await self.get_statement(
                params.model_copy(update={"cursor": cursor})
            )
            for operation in page.operations:
                yield operation
            if not page.next_cursor:
                break
            cursor = page.next_cursor

    async def get_bank_statement(self, params: BankStatementParams) -> BankStatement:
        """Выписка за период: сальдо, обороты и операции."""
        return await self._call(_BANK_STATEMENT, params)

    async def create_ruble_payment(self, payment: CreatePaymentRequest) -> str:
        """Исполнить рублёвый платёж (mTLS). Возвращает id платежа (ключ идемпотентности)."""
        transport = self._pick_transport(secured=True)
        body = payment.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = await transport.request("POST", _RUBLE_TRANSFER_PATH, json=body)
        self._raise_for_http(response)
        return payment.id

    async def get_payment_status(self, payment_id: str) -> PaymentStatusResponse:
        """Статус платежа по его id (mTLS)."""
        transport = self._pick_transport(secured=True)
        response = await transport.request("GET", f"/api/v1/payment/{payment_id}")
        self._raise_for_http(response)
        return PaymentStatusResponse.model_validate(self._parse_body(response))

    async def get_documents_status(
        self, document_ids: List[str]
    ) -> DocumentsStatusResponse:
        """Статусы пачки документов по их id (обычный хост)."""
        return await self._call(
            _DOCUMENTS_STATUS, DocumentsStatusRequest(document_ids=document_ids)
        )

    async def send_invoice(self, request: SendInvoiceRequest) -> SendInvoiceResponse:
        """Выставить счёт клиенту (вернёт invoiceId и ссылку на PDF)."""
        return await self._call(_INVOICE_SEND, request)

    async def get_invoice_info(self, invoice_id: str) -> InvoiceInfo:
        """Статус выставленного счёта."""
        response = await self._transport.request(
            "GET", f"/api/v1/openapi/invoice/{invoice_id}/info"
        )
        self._raise_for_http(response)
        return InvoiceInfo.model_validate(self._parse_body(response))

    async def create_onetime_qr(self, request: CreateOnetimeQrRequest) -> SbpQrResponse:
        """Одноразовая СБП-ссылка/QR для приёма оплаты."""
        return await self._call(_QR_ONETIME, request)

    async def create_reusable_qr(
        self, request: CreateReusableQrRequest
    ) -> SbpQrResponse:
        """Многоразовая СБП-ссылка/QR."""
        return await self._call(_QR_REUSABLE, request)

    async def get_qr_info(
        self, qr_id: str, *, with_image: bool = False
    ) -> SbpQrResponse:
        """Статус СБП-ссылки (опционально с картинкой QR)."""
        response = await self._transport.request(
            "GET", f"/api/v1/b2b/qr/{qr_id}/info", params={"withImage": with_image}
        )
        self._raise_for_http(response)
        return SbpQrResponse.model_validate(self._parse_body(response))
