from __future__ import annotations

from decimal import Decimal
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from tbank.business_cards.enums import (
    CardBlockReason,
    CardIssueApplicationStatus,
    CardNetwork,
    CardStatus,
    InputLimitPeriod,
    OutputLimitPeriod,
    ReissueStatus,
)
from tbank.core.models import Rubles

# Суммы на запись: Decimal у пользователя, но в JSON уходит числом (T-API ждёт number).
WriteRubles = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class BusinessCardModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


# --- Карты ---


class CardInfo(BusinessCardModel):
    ucid: int
    account_number: str
    card_bin: str
    card_last_four_digits: str
    is_active: bool
    status: CardStatus
    embossed_name: str


class CardInfoSeq(BusinessCardModel):
    """Страница карт (метод `/api/v1/card`)."""

    offset: int
    limit: int
    total_number: int
    cards: Optional[List[CardInfo]] = None


class ExpiryDate(BusinessCardModel):
    year: int
    month: int


class VirtualCardRequisites(BusinessCardModel):
    """Реквизиты виртуальной карты (полный номер, CVC, срок)."""

    number: str
    embossed_name: str
    cvc: str
    expiry_date: ExpiryDate


class CompanyCard(BusinessCardModel):
    ucid: int
    account_number: str
    card_bin: str
    card_last_four_digits: str
    embossed_name: str
    is_active: bool
    is_virtual: bool
    status: CardStatus


class CompanyCardsResponse(BusinessCardModel):
    """Список карт компании (метод `/api/v3/company/card`)."""

    cards: List[CompanyCard] = Field(default_factory=list)
    offset: int
    limit: int
    total: Optional[int] = None


# --- Заявки на выпуск виртуальной карты ---


class CreateApplicationRequest(BusinessCardModel):
    employee_identification_application_id: str
    account_number: str
    card_network: CardNetwork


class CreateApplicationResult(BusinessCardModel):
    card_issue_application_id: str


class CardIssueApplicationStatusResult(BusinessCardModel):
    card_issue_application_id: str
    status: CardIssueApplicationStatus
    failed_reason: Optional[str] = None
    ucid: Optional[int] = None


class VirtualCardApplication(BusinessCardModel):
    """Заявка на виртуальную карту (метод `/api/v3/card/virtual/issue/application`)."""

    card_issue_application_id: str
    status: CardIssueApplicationStatus
    ucid: Optional[str] = None


# --- Перевыпуск виртуальной карты ---


class ReissueRequest(BusinessCardModel):
    ucid: int


class ReissueApplication(BusinessCardModel):
    correlation_id: str


class ReissuedVirtualCardInfo(BusinessCardModel):
    old_ucid: int
    new_ucid: int
    card_bin: str
    card_last_four_digits: str


class ReissueVirtualCardResult(BusinessCardModel):
    """Результат перевыпуска: `info` заполнен только при `status == READY`."""

    status: ReissueStatus
    info: Optional[ReissuedVirtualCardInfo] = None


# --- Блокировка ---


class BlockCardRequest(BusinessCardModel):
    reason: CardBlockReason
    comment: Optional[str] = None


# --- Лимиты ---


class SetLimitRequest(BusinessCardModel):
    """Установка лимита (общий расходный или на наличные)."""

    limit_value: WriteRubles
    limit_period: InputLimitPeriod


class SpendLimit(BusinessCardModel):
    limit_value: Rubles
    limit_remain: Rubles
    limit_period: OutputLimitPeriod


class CashLimit(BusinessCardModel):
    limit_value: Rubles
    limit_remain: Rubles
    limit_period: OutputLimitPeriod


class CardLimits(BusinessCardModel):
    ucid: int
    spend_limit: SpendLimit
    cash_limit: CashLimit


# --- Пакетная установка лимитов (v3) ---


class BatchLimitValue(BusinessCardModel):
    limit_period: InputLimitPeriod
    limit_value: int


class BatchLimitItem(BusinessCardModel):
    ucid: int
    spend_limit: Optional[BatchLimitValue] = None
    cash_limit: Optional[BatchLimitValue] = None


class SetBatchLimitsRequest(BusinessCardModel):
    limits: List[BatchLimitItem]


class BatchLimitResult(BusinessCardModel):
    is_success: bool
    error_message: Optional[str] = None


class BatchLimitResultItem(BusinessCardModel):
    ucid: int
    spend_limit: Optional[BatchLimitResult] = None
    cash_limit: Optional[BatchLimitResult] = None


class SetBatchLimitsResult(BusinessCardModel):
    limits: List[BatchLimitResultItem] = Field(default_factory=list)
