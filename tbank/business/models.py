from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from tbank.business.enums import AccountType, OperationStatus, TypeOfOperation
from tbank.core.models import Rubles


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
