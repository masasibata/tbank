from __future__ import annotations

from enum import Enum


class PaymentStatus(str, Enum):
    NEW = "NEW"
    FORM_SHOWED = "FORM_SHOWED"
    AUTHORIZING = "AUTHORIZING"
    AUTHORIZED = "AUTHORIZED"
    CONFIRMING = "CONFIRMING"
    CONFIRMED = "CONFIRMED"
    REVERSING = "REVERSING"
    REVERSED = "REVERSED"
    REFUNDING = "REFUNDING"
    REFUNDED = "REFUNDED"
    PARTIAL_REFUNDED = "PARTIAL_REFUNDED"
    REJECTED = "REJECTED"
    DEADLINE_EXPIRED = "DEADLINE_EXPIRED"
    CANCELED = "CANCELED"


class CardStatus(str, Enum):
    ACTIVE = "A"
    DELETED = "D"
    INACTIVE = "I"  # legacy — в новой спеке не встречается


class CardType(int, Enum):
    DEBIT = 0  # карта списания
    CREDIT = 1  # карта пополнения
    DEBIT_CREDIT = 2  # пополнения и списания
