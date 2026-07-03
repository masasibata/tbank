from __future__ import annotations

from enum import Enum


class AutoPayType(str, Enum):
    """Тип автоматического размещения средств на счёте овернайт."""

    REST_CURRENT = "RestCurrent"
    AMOUNT_OVERNIGHT = "AmountOvernight"
    AMOUNT_CURRENT = "AmountCurrent"
