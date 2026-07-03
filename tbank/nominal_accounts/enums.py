from __future__ import annotations

from enum import Enum


class BeneficiaryType(str, Enum):
    """Тип бенефициара номинального счёта."""

    FL_RESIDENT = "FL_RESIDENT"
    FL_NONRESIDENT = "FL_NONRESIDENT"
    UL_RESIDENT = "UL_RESIDENT"
    UL_NONRESIDENT = "UL_NONRESIDENT"
    IP_RESIDENT = "IP_RESIDENT"
    IP_NONRESIDENT = "IP_NONRESIDENT"
    LITE_CONTACT = "LITE_CONTACT"


class AddressType(str, Enum):
    """Тип адреса бенефициара."""

    POSTAL = "POSTAL_ADDRESS"
    REGISTRATION = "REGISTRATION_ADDRESS"
    RESIDENCE = "RESIDENCE_ADDRESS"
    LEGAL_ENTITY = "LEGAL_ENTITY_ADDRESS"
    OFFICE_OF_FOREIGN_LEGAL_ENTITY = "OFFICE_OF_FOREIGN_LEGAL_ENTITY_ADDRESS"


class DocumentType(str, Enum):
    """Тип документа бенефициара."""

    PASSPORT = "PASSPORT"
    FOREIGN_PASSPORT = "FOREIGN_PASSPORT"
    FOREIGN_PASSPORT_OF_FOREIGN_CITIZENS = "FOREIGN_PASSPORT_OF_FOREIGN_CITIZENS"
    OFFICIAL_PASSPORT = "OFFICIAL_PASSPORT"
    DIPLOMATIC_PASSPORT = "DIPLOMATIC_PASSPORT"
    MIGRATION_CARD = "MIGRATION_CARD"
    TEMPORARY_RESIDENCE_PERMIT = "TEMPORARY_RESIDENCE_PERMIT"
    VISA = "VISA"
    RESIDENCE_PERMIT = "RESIDENCE_PERMIT"
    CONTRACT = "CONTRACT"
    CONTRACT_GPD = "CONTRACT_GPD"
    PATENT = "PATENT"


class BankDetailsType(str, Enum):
    """Тип банковских реквизитов бенефициара."""

    PAYMENT_DETAILS = "PAYMENT_DETAILS"
    CARD = "CARD"
    SBP = "SBP"


class PaymentType(str, Enum):
    """Тип платежа с номинального счёта."""

    REGULAR = "REGULAR"
    TAX = "TAX"


class PaymentStatus(str, Enum):
    """Статус платежа с номинального счёта."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUCCEEDED = "SUCCEEDED"


class DealStatus(str, Enum):
    """Статус сделки."""

    DRAFT = "DRAFT"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class StepStatus(str, Enum):
    """Статус этапа сделки."""

    NEW = "NEW"
    PAYMENT_IN_PROGRESS = "PAYMENT_IN_PROGRESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class AddCardStatus(str, Enum):
    """Статус запроса на добавление карты бенефициара."""

    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"


class ScoringStatus(str, Enum):
    """Статус проверки бенефициара в финансовом мониторинге."""

    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class TransferType(str, Enum):
    """Тип перевода между виртуальными счетами."""

    DIRECT = "DIRECT"
    TO_DEAL = "TO_DEAL"
    FROM_DEAL = "FROM_DEAL"
