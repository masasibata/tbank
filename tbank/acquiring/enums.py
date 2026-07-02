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


class QrDataType(str, Enum):
    PAYLOAD = "PAYLOAD"  # платёжная ссылка/payload
    IMAGE = "IMAGE"  # SVG-изображение QR


class AccountQrStatus(str, Enum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    ACTIVE = "ACTIVE"  # привязка успешна
    INACTIVE = "INACTIVE"  # неуспешна/деактивирована


# --- Фискализация (54-ФЗ) ---


class FfdVersion(str, Enum):
    FFD_105 = "1.05"
    FFD_12 = "1.2"


class Taxation(str, Enum):
    OSN = "osn"
    USN_INCOME = "usn_income"
    USN_INCOME_OUTCOME = "usn_income_outcome"
    ENVD = "envd"
    ESN = "esn"
    PATENT = "patent"


class Tax(str, Enum):
    NONE = "none"
    VAT_0 = "vat0"
    VAT_5 = "vat5"
    VAT_7 = "vat7"
    VAT_10 = "vat10"
    VAT_20 = "vat20"  # legacy (до реформы НДС 2026)
    VAT_22 = "vat22"
    VAT_105 = "vat105"
    VAT_107 = "vat107"
    VAT_110 = "vat110"
    VAT_120 = "vat120"  # legacy
    VAT_122 = "vat122"


class PaymentMethod(str, Enum):
    FULL_PREPAYMENT = "full_prepayment"
    PREPAYMENT = "prepayment"
    ADVANCE = "advance"
    FULL_PAYMENT = "full_payment"
    PARTIAL_PAYMENT = "partial_payment"
    CREDIT = "credit"
    CREDIT_PAYMENT = "credit_payment"


class PaymentObject(str, Enum):
    COMMODITY = "commodity"
    EXCISE = "excise"
    JOB = "job"
    SERVICE = "service"
    GAMBLING_BET = "gambling_bet"
    GAMBLING_PRIZE = "gambling_prize"
    LOTTERY = "lottery"
    LOTTERY_PRIZE = "lottery_prize"
    INTELLECTUAL_ACTIVITY = "intellectual_activity"
    PAYMENT = "payment"
    AGENT_COMMISSION = "agent_commission"
    COMPOSITE = "composite"
    ANOTHER = "another"
