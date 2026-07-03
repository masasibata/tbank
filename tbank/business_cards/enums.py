from __future__ import annotations

from enum import Enum


class CardStatus(str, Enum):
    """Статус бизнес-карты."""

    NORM = "NORM"
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"


class CardNetwork(str, Enum):
    """Платёжная система карты."""

    MASTERCARD = "MASTERCARD"
    VISA = "VISA"
    MIR = "MIR"


class CardBlockReason(str, Enum):
    """Причина блокировки карты."""

    LOST = "LOST"
    STOLEN = "STOLEN"
    BROKEN = "BROKEN"
    FRAUD = "FRAUD"
    CLIENT_INITIATED = "CLIENTINITIATED"


class CardIssueApplicationStatus(str, Enum):
    """Статус заявки на выпуск виртуальной карты."""

    NEW = "NEW"
    IDENTIFICATION = "IDENTIFICATION"
    ISSUING = "ISSUING"
    CARD_ISSUED = "CARD_ISSUED"
    FAILED_FATAL = "FAILED_FATAL"
    FAILED_NON_FATAL = "FAILED_NON_FATAL"


class InputLimitPeriod(str, Enum):
    """Период возобновления лимита (на запись)."""

    DAY = "DAY"
    MONTH = "MONTH"
    IRREGULAR = "IRREGULAR"


class OutputLimitPeriod(str, Enum):
    """Период возобновления лимита (в ответе)."""

    DAY = "DAY"
    MONTH = "MONTH"
    IRREGULAR = "IRREGULAR"
    CUSTOM = "CUSTOM"


class ReissueStatus(str, Enum):
    """Статус заявки на перевыпуск виртуальной карты."""

    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    ERROR = "ERROR"
