from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from tbank.core.models import Kopecks
from tbank.merchant_acquiring.enums import OperationType


class MerchantAcquiringModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class Terminal(MerchantAcquiringModel):
    id: str
    key: str


class TerminalsPage(MerchantAcquiringModel):
    """Страница терминалов торгового эквайринга."""

    total_pages: int
    total_elements: int
    first: bool
    last: bool
    terminals: Optional[List[Terminal]] = None


class Operation(MerchantAcquiringModel):
    """Операция по терминалу (суммы — в копейках)."""

    rrn: str
    transaction_date: datetime
    amount: Kopecks
    card_number: str
    type: OperationType


class OperationList(MerchantAcquiringModel):
    """Операции по терминалу за период."""

    last_transaction_date: Optional[datetime] = None
    operations: Optional[List[Operation]] = None
