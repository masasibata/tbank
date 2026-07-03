from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from tbank.overnight.enums import AutoPayType


class OvernightModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class OvernightAutoPay(OvernightModel):
    """Настройки автоматического размещения средств."""

    is_accessible: bool
    is_active: bool
    type: Optional[AutoPayType] = None


class OvernightDeal(OvernightModel):
    """Информация по текущей сделке овернайт (суммы — строки)."""

    opened: datetime
    closed: datetime
    percent_rate: Optional[str] = None
    amount: Optional[str] = None
    paid_amount: Optional[str] = None


class OvernightSettings(OvernightModel):
    """Настройки счёта овернайт (суммы — строки)."""

    min_amount: str
    max_amount: str
    current_amount: Optional[str] = None
    overnight_amount: Optional[str] = None


class OvernightInfo(OvernightModel):
    """Сводка по счёту овернайт (суммы — строки, как их отдаёт T-API)."""

    agreement_number: str
    amount: str
    blocked_amount: str
    is_accessible: bool
    is_deal_active: bool
    auto_pay: OvernightAutoPay
    actual_deal: OvernightDeal
    settings: OvernightSettings
    percent_rate: Optional[str] = None
    linked_agreement_number: Optional[str] = None
