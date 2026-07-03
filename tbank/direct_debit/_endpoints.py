"""Пути и парсеры безакцептных списаний (общие для sync- и aio-клиентов)."""

from __future__ import annotations

from typing import List, Optional, Sequence

from pydantic import TypeAdapter

from tbank.direct_debit.enums import RuleType
from tbank.direct_debit.models import RuleDetails

V1 = "/api/v1"
V2 = "/api/v2"

# Карточка правила — полиморф (oneOf Recurrent/Trigger) по дискриминатору `type`.
RULE_DETAILS: TypeAdapter[RuleDetails] = TypeAdapter(RuleDetails)


def enum_list(values: Optional[Sequence[RuleType]]) -> Optional[List[str]]:
    """Значения enum'ов для query-параметра (None, если список пуст)."""
    return [v.value for v in values] if values else None
