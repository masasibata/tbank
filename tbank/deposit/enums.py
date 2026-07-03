from __future__ import annotations

from enum import Enum


class Currency(str, Enum):
    """Валюта депозита."""

    RUB = "RUB"
    RUR = "RUR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CNY = "CNY"


class Capitalisation(str, Enum):
    """Признак капитализации процентов."""

    DEPOSIT = "DEPOSIT"
    ACCOUNT = "ACCOUNT"


class PayFrequency(str, Enum):
    """Периодичность выплаты процентов."""

    NORMAL = "NORMAL"
    MATURITY = "MATURITY"


class AutoProlongationStatus(str, Enum):
    """Статус автопролонгации депозита."""

    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    INACCESSIBLE = "INACCESSIBLE"


class DepositAccountStatus(str, Enum):
    """Статус депозитного счёта."""

    OPENED = "OPENED"
    CLOSED = "CLOSED"
    INACTIVE = "INACTIVE"
