from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

from tbank.core.models import Rubles
from tbank.deposit.enums import (
    AutoProlongationStatus,
    Capitalisation,
    Currency,
    DepositAccountStatus,
    PayFrequency,
)

# Суммы на запись: Decimal у пользователя, но в JSON уходит числом (T-API ждёт number).
WriteRubles = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class DepositModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


# --- Карточка депозита ---


class DepositBalance(DepositModel):
    amount: Rubles
    currency_code: str
    paid_amount: Rubles
    locked_amount: Rubles
    fine_amount: Optional[Rubles] = None


class AutoProlongation(DepositModel):
    status: AutoProlongationStatus


class DepositAgreementInfo(DepositModel):
    agreement_number: str
    interest_agreement_number: str
    auto_prolongation: AutoProlongation
    attached_agreement_number: Optional[str] = None
    activation_date: Optional[date] = None
    ending_date: Optional[date] = None
    closing_date: Optional[date] = None
    prolongation_date: Optional[date] = None


class CapitalisationInfo(DepositModel):
    type: Capitalisation


class WithdrawInfo(DepositModel):
    is_accessible: bool
    min_sum: Optional[Rubles] = None


class ReplenishInfo(DepositModel):
    is_accessible: bool


class DepositAccountInfo(DepositModel):
    account_number: str
    status: DepositAccountStatus
    rate: Decimal
    capitalisation: CapitalisationInfo
    min_amount: Rubles
    max_current: Rubles
    max_amount: Rubles
    withdraw: WithdrawInfo
    replenish: ReplenishInfo
    pay_frequency: PayFrequency
    open_date: Optional[date] = None
    name: Optional[str] = None


class DepositAccountDetails(DepositModel):
    """Полная карточка депозита."""

    product: str
    period: int
    balance: DepositBalance
    agreement_info: DepositAgreementInfo
    account_info: DepositAccountInfo


# --- Открытие и пополнение ---


class OpenDepositRequest(DepositModel):
    term: int
    capitalisation: Capitalisation
    currency: Currency
    is_replenish_available: bool
    is_withdraw_available: bool
    pay_frequency: PayFrequency
    linked_account: Optional[str] = None


class OpenDepositResult(DepositModel):
    open_id: str
    application_id: str


class ReplenishDepositRequest(DepositModel):
    deposit_agreement: str
    source_agreement: str
    amount: WriteRubles
