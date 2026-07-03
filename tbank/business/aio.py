from __future__ import annotations

from typing import AsyncIterator, List, Optional

import httpx

from tbank.business import _endpoints
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


class BusinessClient(BaseAsyncClient):
    """Асинхронный клиент T-API (открытый банк Т-Бизнес): счета и выписки."""

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
        return error_from_business_response(response)

    async def get_accounts(self) -> List[Account]:
        """Список счетов с балансами."""
        return await self._get(_endpoints.ACCOUNTS_PATH, _endpoints.ACCOUNTS_ADAPTER)

    async def get_statement(self, params: StatementParams) -> StatementPage:
        """Одна страница выписки операций (курсорная пагинация)."""
        return await self._call(_endpoints.STATEMENT, params)

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
        return await self._call(_endpoints.BANK_STATEMENT, params)

    async def create_ruble_payment(self, payment: CreatePaymentRequest) -> str:
        """Исполнить рублёвый платёж (mTLS). Возвращает id платежа (ключ идемпотентности)."""
        await self._send(
            "POST", _endpoints.RUBLE_TRANSFER_PATH, body=payment, secured=True
        )
        return payment.id

    async def get_payment_status(self, payment_id: str) -> PaymentStatusResponse:
        """Статус платежа по его id (mTLS)."""
        return await self._get(
            _endpoints.payment_path(payment_id), PaymentStatusResponse, secured=True
        )

    async def get_documents_status(
        self, document_ids: List[str]
    ) -> DocumentsStatusResponse:
        """Статусы пачки документов по их id (обычный хост)."""
        return await self._call(
            _endpoints.DOCUMENTS_STATUS,
            DocumentsStatusRequest(document_ids=document_ids),
        )

    async def send_invoice(self, request: SendInvoiceRequest) -> SendInvoiceResponse:
        """Выставить счёт клиенту (вернёт invoiceId и ссылку на PDF)."""
        return await self._call(_endpoints.INVOICE_SEND, request)

    async def get_invoice_info(self, invoice_id: str) -> InvoiceInfo:
        """Статус выставленного счёта."""
        return await self._get(_endpoints.invoice_info_path(invoice_id), InvoiceInfo)

    async def create_onetime_qr(self, request: CreateOnetimeQrRequest) -> SbpQrResponse:
        """Одноразовая СБП-ссылка/QR для приёма оплаты."""
        return await self._call(_endpoints.QR_ONETIME, request)

    async def create_reusable_qr(
        self, request: CreateReusableQrRequest
    ) -> SbpQrResponse:
        """Многоразовая СБП-ссылка/QR."""
        return await self._call(_endpoints.QR_REUSABLE, request)

    async def get_qr_info(
        self, qr_id: str, *, with_image: bool = False
    ) -> SbpQrResponse:
        """Статус СБП-ссылки (опционально с картинкой QR)."""
        return await self._get(
            _endpoints.qr_info_path(qr_id),
            SbpQrResponse,
            params={"withImage": with_image},
        )
