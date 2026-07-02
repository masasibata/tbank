from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from tbank.business.enums import (
    AccountType,
    OperationStatus,
    PaymentStatus,
    TypeOfOperation,
)
from tbank.core.models import Rubles

# Суммы на запись: Decimal у пользователя, но в JSON уходит числом (T-API ждёт number).
WriteRubles = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class BusinessModel(BaseModel):
    """Базовая модель T-API: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


# --- Счета ---


class Balance(BusinessModel):
    otb: Optional[Rubles] = None  # доступный остаток
    authorized: Optional[Rubles] = None  # заблокировано (холды)
    pending_payments: Optional[Rubles] = None
    pending_requisitions: Optional[Rubles] = None


class TransitAccount(BusinessModel):
    account_number: Optional[str] = None


class Account(BusinessModel):
    account_number: str
    name: str
    currency: str  # числовой код ОКВ, напр. "643"
    bank_bik: str
    account_type: AccountType
    balance: Optional[Balance] = None
    transit_account: Optional[TransitAccount] = None


# --- Выписка (statement, курсорная пагинация) ---


class StatementParams(BusinessModel):
    account_number: str
    from_: datetime = Field(alias="from")  # включительно
    to: Optional[datetime] = None  # не включительно
    cursor: Optional[str] = None
    limit: Optional[int] = None
    with_balances: Optional[bool] = None
    operation_status: Optional[OperationStatus] = None


class Counterparty(BusinessModel):
    account: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    name: Optional[str] = None
    bank_name: Optional[str] = None
    bic_ru: Optional[str] = None


class StatementOperation(BusinessModel):
    operation_id: str
    operation_date: datetime
    operation_status: Optional[OperationStatus] = None
    type_of_operation: Optional[TypeOfOperation] = None
    category: Optional[str] = None
    operation_amount: Optional[Rubles] = None
    account_amount: Optional[Rubles] = None
    ruble_amount: Optional[Rubles] = None
    pay_purpose: Optional[str] = None
    payer: Optional[Counterparty] = None
    receiver: Optional[Counterparty] = None
    counter_party: Optional[Counterparty] = None


class StatementBalances(BusinessModel):
    balance_begin: Optional[Rubles] = None
    balance_end: Optional[Rubles] = None
    credit: Optional[Rubles] = None
    debit: Optional[Rubles] = None


class StatementPage(BusinessModel):
    balances: Optional[StatementBalances] = None
    operations: List[StatementOperation] = Field(default_factory=list)
    next_cursor: Optional[str] = None


# --- Выписка за период (bank-statement) ---


class BankStatementParams(BusinessModel):
    account_number: str
    from_: Optional[date] = Field(default=None, alias="from")
    till: Optional[date] = None


class BankStatementOperation(BusinessModel):
    id: Optional[str] = None
    date: Optional[date] = None
    amount: Optional[Rubles] = None
    payment_purpose: Optional[str] = None
    payer_name: Optional[str] = None
    payer_inn: Optional[str] = None
    payer_kpp: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_inn: Optional[str] = None
    recipient_kpp: Optional[str] = None


class BankStatement(BusinessModel):
    saldo_in: Optional[Rubles] = None
    income: Optional[Rubles] = None
    outcome: Optional[Rubles] = None
    saldo_out: Optional[Rubles] = None
    operation: List[BankStatementOperation] = Field(default_factory=list)


# --- Платежи (рублёвая платёжка, mTLS) ---


class PaymentFrom(BusinessModel):
    account_number: str


class ReceiverRequisites(BusinessModel):
    name: str
    inn: str
    account_number: str
    bik: str
    kpp: Optional[str] = None
    bank_name: Optional[str] = None
    corr_account_number: Optional[str] = None


class ThirdParty(BusinessModel):
    inn: str
    kpp: str
    name: Optional[str] = None


class TaxPaymentParameters(BusinessModel):
    payer_status: str
    kbk: str
    oktmo: str
    evidence: str
    period: str  # формат ДД.ММ.ГГГГ (строка, НЕ дата)
    doc_number: str
    doc_date: str  # формат ДД.ММ.ГГГГ
    third_party: Optional[ThirdParty] = None


class CreatePaymentRequest(BusinessModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # ключ идемпотентности
    from_: PaymentFrom = Field(alias="from")
    to: ReceiverRequisites
    purpose: str
    amount: WriteRubles
    document_number: Optional[int] = None
    execution_order: Optional[int] = None
    due_date: Optional[datetime] = None
    uin: Optional[str] = None
    tax: Optional[TaxPaymentParameters] = None
    revenue_type_code: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class PaymentStatusResponse(BusinessModel):
    status: PaymentStatus
    error_message: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class DocumentsStatusRequest(BusinessModel):
    document_ids: List[str]


class DocumentStatus(BusinessModel):
    document_id: Optional[str] = None
    status: Optional[str] = None


class DocumentStatusError(BusinessModel):
    document_id: Optional[str] = None
    error_message: Optional[str] = None


class DocumentsStatusResponse(BusinessModel):
    result: List[DocumentStatus] = Field(default_factory=list)
    result_error: List[DocumentStatusError] = Field(default_factory=list)
