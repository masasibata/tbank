"""Эндпоинты открытого банка Т-Бизнес (общие для sync- и aio-клиентов)."""

from __future__ import annotations

from typing import List

from pydantic import TypeAdapter

from tbank.business.models import (
    Account,
    BankStatement,
    BankStatementParams,
    CreateOnetimeQrRequest,
    CreateReusableQrRequest,
    DocumentsStatusRequest,
    DocumentsStatusResponse,
    SbpQrResponse,
    SendInvoiceRequest,
    SendInvoiceResponse,
    StatementPage,
    StatementParams,
)
from tbank.core.endpoint import Endpoint

ACCOUNTS_PATH = "/api/v2/bank-accounts"
RUBLE_TRANSFER_PATH = "/api/v1/payment/ruble-transfer/pay"

STATEMENT = Endpoint("GET", "/api/v1/statement", StatementPage, StatementParams)
BANK_STATEMENT = Endpoint(
    "GET", "/api/v1/bank-statement", BankStatement, BankStatementParams
)
DOCUMENTS_STATUS = Endpoint(
    "POST", "/api/v1/payment/status", DocumentsStatusResponse, DocumentsStatusRequest
)
INVOICE_SEND = Endpoint(
    "POST", "/api/v1/invoice/send", SendInvoiceResponse, SendInvoiceRequest
)
QR_ONETIME = Endpoint(
    "POST", "/api/v1/b2b/qr/onetime", SbpQrResponse, CreateOnetimeQrRequest
)
QR_REUSABLE = Endpoint(
    "POST", "/api/v1/b2b/qr/reusable", SbpQrResponse, CreateReusableQrRequest
)

ACCOUNTS_ADAPTER: TypeAdapter[List[Account]] = TypeAdapter(List[Account])


def payment_path(payment_id: str) -> str:
    return f"/api/v1/payment/{payment_id}"


def invoice_info_path(invoice_id: str) -> str:
    return f"/api/v1/openapi/invoice/{invoice_id}/info"


def qr_info_path(qr_id: str) -> str:
    return f"/api/v1/b2b/qr/{qr_id}/info"
