from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from tbank.core.models import Rubles
from tbank.selfemployed.enums import (
    AddressKind,
    DocumentType,
    DraftStatus,
    IncomeType,
    PaymentInfoStatus,
    PaymentResultStatus,
    PayResultStatus,
    PhoneType,
    ReceiptsRequestStatus,
    ReceiptStatus,
    RecipientStatus,
    RegistryCreateType,
    RegistryStatus,
    RevenueTypeCode,
    SelfEmployedAgreementStatus,
    SelfEmployedIdentificationStatus,
    SelfEmployedStatus,
    SubmitResultStatus,
)

# Суммы на запись: Decimal у пользователя, но в JSON уходит числом (T-API ждёт number).
WriteRubles = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class SelfEmployedModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


def _correlation_id() -> str:
    return str(uuid.uuid4())


class CorrelatedRequest(SelfEmployedModel):
    """Запрос-инициатор async-операции с клиентским correlationId."""

    correlation_id: str = Field(default_factory=_correlation_id)


# --- Общие ошибки (три формы в разных ответах T-API) ---


class FieldError(SelfEmployedModel):
    field_name: str
    error_description: str


class CodeMessageError(SelfEmployedModel):
    error_code: str
    error_message: str


class CodeDescriptionError(SelfEmployedModel):
    error_code: str
    error_description: str


# --- Самозанятые: анкеты (recipients/create) ---


class RecipientPhone(SelfEmployedModel):
    type: PhoneType
    number: str


class RecipientAddress(SelfEmployedModel):
    type: AddressKind
    postal_code: str
    state: str
    country: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    settlement: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None
    building: Optional[str] = None
    construction: Optional[str] = None
    apartment: Optional[str] = None


class RecipientDocument(SelfEmployedModel):
    type: DocumentType
    serial: str
    issued_on: date = Field(alias="date")
    organization: str
    number: Optional[str] = None
    division: Optional[str] = None
    expire_date: Optional[date] = None


class RegistrationInfo(SelfEmployedModel):
    oktmo: str
    activity_codes: List[str] = Field(default_factory=list)


class RecipientDraft(SelfEmployedModel):
    number: int
    first_name: str
    last_name: str
    birth_date: date
    birth_place: str
    citizenship: str
    middle_name: Optional[str] = None
    email: Optional[str] = None
    latin_first_name: Optional[str] = None
    latin_last_name: Optional[str] = None
    phones: Optional[List[RecipientPhone]] = None
    addresses: Optional[List[RecipientAddress]] = None
    documents: Optional[List[RecipientDocument]] = None
    registration_info: Optional[RegistrationInfo] = None


class CreateRecipientsRequest(CorrelatedRequest):
    recipients: List[RecipientDraft]


class RecipientResult(SelfEmployedModel):
    number: int
    first_name: str
    last_name: str
    status: DraftStatus
    recipient_id: Optional[int] = None
    middle_name: Optional[str] = None
    errors: List[FieldError] = Field(default_factory=list)


class RecipientResults(SelfEmployedModel):
    recipient_results: List[RecipientResult] = Field(default_factory=list)


# --- Самозанятые: добавление по реквизитам (recipients/add/by-requisites) ---


class RecipientBankInfo(SelfEmployedModel):
    account_number: str
    bank_bic: Optional[str] = None


class RecipientByRequisites(SelfEmployedModel):
    number: int
    first_name: str
    last_name: str
    bank_info: RecipientBankInfo
    middle_name: Optional[str] = None
    mobile_number: Optional[str] = None
    inn: Optional[str] = None


class AddRecipientsByRequisitesRequest(CorrelatedRequest):
    recipients: List[RecipientByRequisites]


# --- Самозанятые: список (recipients/list) ---


class DateRange(SelfEmployedModel):
    from_: Optional[datetime] = Field(default=None, alias="from")
    to: Optional[datetime] = None


class ListRecipientsRequest(SelfEmployedModel):
    recipient_ids: Optional[List[int]] = None
    inn: Optional[List[str]] = None
    status: Optional[List[str]] = None
    self_employed_status: Optional[List[str]] = None
    creation_date: Optional[DateRange] = None
    offset: Optional[int] = None
    limit: Optional[int] = None


class RecipientBankInfoFull(SelfEmployedModel):
    account_number: Optional[str] = None
    agreement_number: Optional[str] = None
    bank_bic: Optional[str] = None


class RecipientInfo(SelfEmployedModel):
    id: int
    status: RecipientStatus
    self_employed_status: SelfEmployedStatus
    self_employed_identification_status: SelfEmployedIdentificationStatus
    self_employed_agreement_status: SelfEmployedAgreementStatus
    first_name: str
    last_name: str
    bank_info: RecipientBankInfoFull
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    phones: Optional[List[RecipientPhone]] = None
    documents: Optional[List[RecipientDocument]] = None
    registration_info: Optional[RegistrationInfo] = None
    inn: Optional[str] = None
    creation_date: Optional[datetime] = None


class ListRecipientsResult(SelfEmployedModel):
    recipients: List[RecipientInfo] = Field(default_factory=list)


# --- Реестр: создание черновика (payment-registry/create) ---


class SelfEmployedInfo(SelfEmployedModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None


class RegistryPayment(SelfEmployedModel):
    number: int
    account_number: str
    payment_purpose: str
    self_employed_info: SelfEmployedInfo
    sum: WriteRubles
    revenue_type_code: Optional[RevenueTypeCode] = None
    collection_amount: Optional[WriteRubles] = None


class CreatePaymentRegistryRequest(CorrelatedRequest):
    payments: List[RegistryPayment]
    company_account_number: Optional[str] = None
    registry_create_type: Optional[RegistryCreateType] = None
    tax_holding: Optional[bool] = None
    income_type: Optional[IncomeType] = None


class PaymentError(SelfEmployedModel):
    number: int
    account_number: Optional[str] = None
    errors: List[FieldError] = Field(default_factory=list)


class CreateRegistryResult(SelfEmployedModel):
    status: DraftStatus
    payment_registry_id: Optional[int] = None
    error: Optional[FieldError] = None
    payment_errors: List[PaymentError] = Field(default_factory=list)


# --- Реестр: подписание / оплата / чеки (submit / pay / receipts) ---


class SubmitRegistryResult(SelfEmployedModel):
    payment_registry_id: int
    status: SubmitResultStatus
    error: Optional[CodeMessageError] = None
    payment_errors: List[PaymentError] = Field(default_factory=list)


class PaymentResult(SelfEmployedModel):
    number: int
    payment_status: PaymentResultStatus
    account_number: Optional[str] = None
    errors: List[FieldError] = Field(default_factory=list)


class PayRegistryResult(SelfEmployedModel):
    payment_registry_id: int
    status: PayResultStatus
    count: int
    error: Optional[CodeDescriptionError] = None
    payment_results: List[PaymentResult] = Field(default_factory=list)


class ReceiptSelfEmployedInfo(SelfEmployedModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    inn: Optional[str] = None
    recipient_id: Optional[int] = None


class Receipt(SelfEmployedModel):
    number: int
    self_employed_info: ReceiptSelfEmployedInfo
    status: ReceiptStatus
    link: Optional[str] = None
    sum: Optional[Rubles] = None
    comment: Optional[str] = None
    error: Optional[CodeMessageError] = None


class ReceiptsResult(SelfEmployedModel):
    status: ReceiptsRequestStatus
    error: Optional[CodeMessageError] = None
    receipts: List[Receipt] = Field(default_factory=list)


# --- Реестр: список и карточка (list / {id}) ---


class ListRegistriesRequest(SelfEmployedModel):
    offset: Optional[int] = None
    statuses: Optional[List[RegistryStatus]] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class PaymentOrder(SelfEmployedModel):
    number: int
    created_at: datetime = Field(alias="date")
    count: int
    sum: Rubles
    status: RegistryStatus


class ListRegistriesResult(SelfEmployedModel):
    payment_orders: List[PaymentOrder] = Field(default_factory=list)


class RegistryPaymentInfo(SelfEmployedModel):
    status: PaymentInfoStatus
    self_employed_info: SelfEmployedInfo
    sum: Rubles
    number: Optional[int] = None
    account_number: Optional[str] = None
    payment_purpose: Optional[str] = None
    revenue_type_code: Optional[RevenueTypeCode] = None
    collection_amount: Optional[Rubles] = None


class PaymentRegistryInfo(SelfEmployedModel):
    status: RegistryStatus
    payments_count: int
    total_sum: Rubles
    load_date: Optional[str] = None
    payments: List[RegistryPaymentInfo] = Field(default_factory=list)


# --- Служебные модели запросов (инициатор / поллинг по correlationId) ---


class RegistryActionRequest(CorrelatedRequest):
    """Тело submit/pay/receipts: {correlationId, paymentRegistryId}."""

    payment_registry_id: int


class CorrelationRef(SelfEmployedModel):
    """Ссылка по correlationId (query для GET-результатов, тело для pay/result)."""

    correlation_id: str
