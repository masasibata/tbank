from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from tbank.core.models import Rubles
from tbank.direct_debit.enums import (
    AgreementParticipant,
    AgreementStatus,
    DocType,
    PaymentCondition,
    PaymentDirection,
    PaymentRequestStatus,
    ReplenishmentCategory,
    RuleType,
)

# Суммы на запись: Decimal у пользователя, но в JSON уходит числом (T-API ждёт number).
WriteRubles = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class DirectDebitModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class _Paged(DirectDebitModel):
    """Общие поля страничного ответа."""

    offset: int
    limit: int
    size: int
    total: int


# --- Реквизиты платёжного требования ---


class PaymentRequisites(DirectDebitModel):
    """Реквизиты платёжного требования (списание/пополнение)."""

    payer_account: str
    payer_name: str
    payer_inn: str = Field(alias="payerINN")
    payer_kpp: str = Field(alias="payerKPP")
    payer_bic: str = Field(alias="payerBIC")
    payer_cor_account: str
    recipient_account: str
    purpose: str
    doc_type: DocType = DocType.PAYMENT_REQUEST
    amount: Optional[WriteRubles] = None
    payment_condition: Optional[PaymentCondition] = None
    accept_term: Optional[int] = None
    doc_dispatch_date: Optional[date] = None


class CreatePaymentRequest(PaymentRequisites):
    """Тело создания платёжного требования (POST /requests)."""

    document_number: Optional[int] = None
    agreement_id: Optional[str] = None


# --- Правила: триггерные параметры ---


class TriggerAmount(DirectDebitModel):
    """Сумма триггерного правила: фиксированная или процент от пополнения."""

    fixed: Optional[WriteRubles] = None
    percent: Optional[WriteRubles] = None


class ReplenishmentPayer(DirectDebitModel):
    inn: str
    kpp: str


class ReplenishmentFilter(DirectDebitModel):
    """Условия срабатывания триггерного правила по операциям пополнения."""

    category: ReplenishmentCategory
    payers: Optional[List[ReplenishmentPayer]] = None


# --- Правила: создание (дискриминатор `type`) ---


class RecurrentRuleCreate(DirectDebitModel):
    type: Literal["Recurrent"] = "Recurrent"
    agreement_id: str
    cron_expr: str
    requisites: PaymentRequisites


class TriggerRuleCreate(DirectDebitModel):
    type: Literal["Trigger"] = "Trigger"
    agreement_id: str
    amount: TriggerAmount
    replenishment_filter: ReplenishmentFilter
    requisites: PaymentRequisites


RuleCreate = Annotated[
    Union[RecurrentRuleCreate, TriggerRuleCreate], Field(discriminator="type")
]


# --- Правила: обновление (дискриминатор `type`) ---


class RecurrentRuleUpdate(DirectDebitModel):
    type: Literal["Recurrent"] = "Recurrent"
    cron_expr: str
    requisites: PaymentRequisites


class TriggerRuleUpdate(DirectDebitModel):
    type: Literal["Trigger"] = "Trigger"
    amount: TriggerAmount
    replenishment_filter: ReplenishmentFilter
    requisites: PaymentRequisites


RuleUpdate = Annotated[
    Union[RecurrentRuleUpdate, TriggerRuleUpdate], Field(discriminator="type")
]


# --- Правила: карточка (дискриминатор `type`) ---


class RecurrentRuleDetails(DirectDebitModel):
    type: Literal["Recurrent"] = "Recurrent"
    id: str
    agreement_id: str
    cron_expr: str
    requisites: PaymentRequisites


class TriggerRuleDetails(DirectDebitModel):
    type: Literal["Trigger"] = "Trigger"
    id: str
    agreement_id: str
    amount: TriggerAmount
    replenishment_filter: ReplenishmentFilter
    requisites: PaymentRequisites


RuleDetails = Annotated[
    Union[RecurrentRuleDetails, TriggerRuleDetails], Field(discriminator="type")
]


class RuleListItem(DirectDebitModel):
    type: RuleType
    id: str
    amount: Rubles
    cron_expr: str


class RuleListResponse(_Paged):
    results: Optional[List[RuleListItem]] = None


class RuleDetailsListResponse(_Paged):
    results: Optional[List[RuleDetails]] = None


class CreateRuleResult(DirectDebitModel):
    rule_id: str


# --- Платёжные требования ---


class PaymentRequestListItem(DirectDebitModel):
    id: str
    creation_date: date
    doc_type: DocType
    direction: PaymentDirection
    status: PaymentRequestStatus


class PaymentRequestListResponse(_Paged):
    results: Optional[List[PaymentRequestListItem]] = None


class PaymentRequestDetails(DirectDebitModel):
    id: str
    creation_date: date
    doc_type: DocType
    amount: Rubles
    payer_account: str
    payer_name: str
    payer_inn: str = Field(alias="payerINN")
    recipient_account: str
    purpose: str
    direction: PaymentDirection
    status: PaymentRequestStatus
    payer_kpp: Optional[str] = Field(default=None, alias="payerKPP")
    payer_bic: Optional[str] = Field(default=None, alias="payerBIC")
    payer_cor_account: Optional[str] = None
    payment_condition: Optional[PaymentCondition] = None
    accept_term: Optional[int] = None
    doc_dispatch_date: Optional[date] = None
    document_number: Optional[int] = None
    agreement_id: Optional[str] = None
    rule_id: Optional[str] = None


class CreatePaymentRequestResult(DirectDebitModel):
    id: str


class PaymentRequestFile(DirectDebitModel):
    """PDF платёжного требования (`content` — base64)."""

    content: str


# --- Соглашения ---


class AgreementListItem(DirectDebitModel):
    id: str
    type: Optional[AgreementParticipant] = None
    status: Optional[AgreementStatus] = None


class AgreementListResponse(_Paged):
    results: Optional[List[AgreementListItem]] = None


class AgreementRequisites(DirectDebitModel):
    name: Optional[str] = None
    address: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    ogrn: Optional[str] = None
    signer_name: Optional[str] = None
    signer_position: Optional[str] = None
    signer_document: Optional[str] = None
    account_number: Optional[str] = None
    account_currency: Optional[str] = None
    cor_account_number: Optional[str] = None
    bic: Optional[str] = None
    bank_name: Optional[str] = None


class AgreementDetails(DirectDebitModel):
    id: str
    number: str
    recipient_requisites: AgreementRequisites
    payer_requisites: AgreementRequisites
    start_date: datetime
    end_date: Optional[datetime] = None
    max_sum: Optional[Rubles] = None
    currency: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[AgreementStatus] = None


class AgreementFile(DirectDebitModel):
    """PDF соглашения (`content` — base64)."""

    filename: str
    content: str


class AgreementUrl(DirectDebitModel):
    url: str
