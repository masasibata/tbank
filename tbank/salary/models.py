from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from tbank.core.models import Rubles
from tbank.salary.enums import (
    AddressKind,
    CancelStatus,
    DocumentType,
    DraftStatus,
    EmployeeStatus,
    PaymentInfoStatus,
    PhoneType,
    RegistryCreateType,
    RegistryStatus,
    RevenueTypeCode,
    SubmitResultStatus,
)

# Суммы на запись: Decimal у пользователя, но в JSON уходит числом (T-API ждёт number).
WriteRubles = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class SalaryModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


def _correlation_id() -> str:
    return str(uuid.uuid4())


class CorrelatedRequest(SalaryModel):
    """Запрос-инициатор async-операции с клиентским correlationId."""

    correlation_id: str = Field(default_factory=_correlation_id)


# --- Общие ошибки ---


class FieldError(SalaryModel):
    field_name: str
    error_description: str


class CodeMessageError(SalaryModel):
    error_code: str
    error_message: str


class CodeDescriptionError(SalaryModel):
    error_code: str
    error_description: Optional[str] = None


class PaymentError(SalaryModel):
    number: int
    account_number: Optional[str] = None
    errors: List[FieldError] = Field(default_factory=list)


class EmployeeResult(SalaryModel):
    number: int
    first_name: str
    last_name: str
    status: DraftStatus
    employee_id: Optional[int] = None
    middle_name: Optional[str] = None
    errors: List[FieldError] = Field(default_factory=list)


# --- Сотрудники: добавление по реквизитам ---


class EmployeeBankInfo(SalaryModel):
    account_number: str
    bank_bic: Optional[str] = None


class EmployeeByRequisites(SalaryModel):
    number: int
    first_name: str
    last_name: str
    bank_info: EmployeeBankInfo
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    passport_serial: Optional[str] = None
    passport_number: Optional[str] = None
    mobile_number: Optional[str] = None
    email: Optional[str] = None


class AddEmployeesByRequisitesRequest(CorrelatedRequest):
    employees: List[EmployeeByRequisites]


class AddEmployeesResult(SalaryModel):
    employees_results: List[EmployeeResult] = Field(default_factory=list)


# --- Сотрудники: анкеты (salary/employees/create) ---


class EmployeePhone(SalaryModel):
    type: PhoneType
    number: str


class EmployeeAddress(SalaryModel):
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


class EmployeeDocument(SalaryModel):
    type: DocumentType
    serial: str
    issued_on: date = Field(alias="date")
    organization: str
    number: Optional[str] = None
    division: Optional[str] = None
    expire_date: Optional[date] = None


class JobInfo(SalaryModel):
    position: Optional[str] = None


class EmployeeDraft(SalaryModel):
    number: int
    first_name: str
    last_name: str
    birth_date: date
    birth_place: str
    citizenship: str
    job_info: JobInfo
    middle_name: Optional[str] = None
    email: Optional[str] = None
    latin_first_name: Optional[str] = None
    latin_last_name: Optional[str] = None
    phones: Optional[List[EmployeePhone]] = None
    addresses: Optional[List[EmployeeAddress]] = None
    documents: Optional[List[EmployeeDocument]] = None


class CreateEmployeesRequest(CorrelatedRequest):
    employees: List[EmployeeDraft]


class CreateEmployeesResult(SalaryModel):
    employee_results: List[EmployeeResult] = Field(default_factory=list)


# --- Сотрудники: список ---


class EmployeeBankInfoFull(SalaryModel):
    account_number: Optional[str] = None
    agreement_number: Optional[str] = None


class EmployeeInfo(SalaryModel):
    id: int
    status: EmployeeStatus
    first_name: str
    last_name: str
    bank_info: EmployeeBankInfoFull
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    phones: Optional[List[EmployeePhone]] = None
    documents: Optional[List[EmployeeDocument]] = None
    job_info: Optional[JobInfo] = None


class ListEmployeesRequest(SalaryModel):
    employee_ids: List[int]


class ListEmployeesResult(SalaryModel):
    employees: List[EmployeeInfo] = Field(default_factory=list)


# --- Реестр: создание черновика / создание-и-подписание ---


class RegistryEmployeeInfo(SalaryModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    employee_id: Optional[int] = None


class RegistryPayment(SalaryModel):
    number: int
    account_number: str
    payment_purpose: str
    employee_info: RegistryEmployeeInfo
    sum: WriteRubles
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    revenue_type_code: Optional[RevenueTypeCode] = None
    collection_amount: Optional[WriteRubles] = None


class CreatePaymentRegistryRequest(CorrelatedRequest):
    payments: Optional[List[RegistryPayment]] = None
    company_account_number: Optional[str] = None
    load_date: Optional[str] = None
    registry_create_type: Optional[RegistryCreateType] = None


class CreateSubmitRegistryRequest(CorrelatedRequest):
    payments: List[RegistryPayment]
    company_account_number: Optional[str] = None
    load_date: Optional[datetime] = None
    registry_create_type: Optional[RegistryCreateType] = None


class CreateRegistryResult(SalaryModel):
    status: DraftStatus
    payment_registry_id: Optional[int] = None
    error: Optional[FieldError] = None
    payment_errors: List[PaymentError] = Field(default_factory=list)


class CreateSubmitResult(SalaryModel):
    status: SubmitResultStatus
    payment_registry_id: Optional[int] = None
    error: Optional[CodeMessageError] = None
    payment_errors: List[PaymentError] = Field(default_factory=list)


# --- Реестр: подписание / оплата / отмена ---


class RegistryActionRequest(CorrelatedRequest):
    """Тело submit: {correlationId, paymentRegistryId}."""

    payment_registry_id: int


class SubmitResult(SalaryModel):
    payment_registry_id: int
    status: SubmitResultStatus
    error: Optional[CodeMessageError] = None
    payment_errors: List[PaymentError] = Field(default_factory=list)


class PayRegistryRequest(SalaryModel):
    """Оплата реестра: `id` — ключ идемпотентности (генерируется автоматически)."""

    payment_registry_id: int
    account_number: str
    purpose: str
    id: str = Field(default_factory=_correlation_id)
    document_number: Optional[int] = None
    execution_order: Optional[int] = None
    due_date: Optional[datetime] = None
    meta: Optional[Dict[str, Any]] = None


class CancelRequest(CorrelatedRequest):
    payment_order_number: int


class CancelResult(SalaryModel):
    status: CancelStatus
    error: Optional[CodeDescriptionError] = None


# --- Реестр: список и карточка ---


class ListRegistriesRequest(SalaryModel):
    offset: Optional[int] = None
    statuses: Optional[List[RegistryStatus]] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class PaymentOrder(SalaryModel):
    number: int
    created_at: datetime = Field(alias="date")
    count: int
    sum: Rubles
    status: RegistryStatus


class ListRegistriesResult(SalaryModel):
    payment_orders: List[PaymentOrder] = Field(default_factory=list)


class RegistryPaymentInfo(SalaryModel):
    status: PaymentInfoStatus
    employee_info: RegistryEmployeeInfo
    sum: Rubles
    number: Optional[int] = None
    account_number: Optional[str] = None
    payment_purpose: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class PaymentRegistryInfo(SalaryModel):
    status: RegistryStatus
    payments_count: int
    total_sum: Rubles
    company_account_number: Optional[str] = None
    load_date: Optional[str] = None
    payments: List[RegistryPaymentInfo] = Field(default_factory=list)


# --- Служебное ---


class CorrelationRef(SalaryModel):
    """Ссылка по correlationId (query для GET-результатов)."""

    correlation_id: str
