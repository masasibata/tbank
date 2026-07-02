from __future__ import annotations

from decimal import Decimal
from typing import Union

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_pascal

Kopecks = int


class TBankModel(BaseModel):
    """Базовая модель: snake_case в Python, PascalCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True,
        extra="ignore",
    )


def to_kopecks(rubles: Union[Decimal, int, str]) -> Kopecks:
    """Рубли → целые копейки."""
    return int((Decimal(str(rubles)) * 100).to_integral_value())


def to_rubles(kopecks: Kopecks) -> Decimal:
    """Копейки → рубли (Decimal)."""
    return Decimal(kopecks) / 100
