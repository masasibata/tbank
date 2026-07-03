from __future__ import annotations

from enum import Enum


class RuleType(str, Enum):
    """Тип правила безакцептного списания."""

    RECURRENT = "Recurrent"
    TRIGGER = "Trigger"


class DocType(str, Enum):
    """Тип платёжного документа."""

    PAYMENT_REQUEST = "PaymentRequest"


class PaymentCondition(str, Enum):
    """Условие платежа."""

    WITH_ACCEPTANCE = "WithAcceptance"
    WITHOUT_ACCEPTANCE = "WithoutAcceptance"


class PaymentDirection(str, Enum):
    """Направление платёжного требования."""

    DEBIT = "Debit"
    CREDIT = "Credit"


class PaymentRequestStatus(str, Enum):
    """Статус платёжного требования."""

    PENDING = "Pending"
    SENT = "Sent"
    REVOKED = "Revoked"
    ARCHIVED = "Archived"
    ERROR = "Error"
    DECLINED = "Declined"
    CARD = "Card"
    ACCEPTED = "Accepted"
    OUTDATED = "Outdated"
    PARTIAL = "Partial"
    REVOKE_REQUESTED = "RevokeRequested"
    COMPLETED = "Completed"


class AgreementStatus(str, Enum):
    """Статус соглашения о безакцептном списании."""

    PENDING = "Pending"
    ACTIVE = "Active"
    SIGNED = "Signed"
    TERMINATED = "Terminated"
    ERROR = "Error"
    OUTDATED = "Outdated"


class AgreementParticipant(str, Enum):
    """Тип участия компании в соглашении."""

    RECIPIENT = "Recipient"
    PAYER = "Payer"


class ReplenishmentCategory(str, Enum):
    """Категория операций пополнения для триггерного правила."""

    CASH_IN = "CashIn"
    MERCHANT_ACQ = "MerchantAcq"
    INTERNET_ACQ = "InternetAcq"
    COUNTERPARTY_INCOME = "CounterpartyIncome"
