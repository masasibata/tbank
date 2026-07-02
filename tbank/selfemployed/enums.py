from __future__ import annotations

from enum import Enum


class RegistryCreateType(str, Enum):
    """Поведение при ошибках в платежах реестра."""

    IGNORE_ERRORS = "IGNORE_ERRORS"
    FAIL_ERRORS = "FAIL_ERRORS"


class IncomeType(str, Enum):
    """Источник дохода самозанятого."""

    FROM_LEGAL_ENTITY = "FROM_LEGAL_ENTITY"
    FROM_INDIVIDUAL = "FROM_INDIVIDUAL"


class RevenueTypeCode(str, Enum):
    """Код вида выплаты (1–5)."""

    CODE_1 = "1"
    CODE_2 = "2"
    CODE_3 = "3"
    CODE_4 = "4"
    CODE_5 = "5"


class DraftStatus(str, Enum):
    """Статус черновика (анкеты самозанятого / реестра) в async-результате."""

    QUEUED = "QUEUED"
    CREATED = "CREATED"
    ERROR = "ERROR"


class RegistryStatus(str, Enum):
    """Статус платёжного реестра (список / карточка)."""

    DRAFT = "DRAFT"
    ERROR = "ERROR"
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    ACCEPTED = "ACCEPTED"
    EXECUTED = "EXECUTED"
    PART_EXEC = "PART_EXEC"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    DELETED = "DELETED"


class SubmitResultStatus(str, Enum):
    """Статус подписания реестра."""

    IN_PROGRESS = "IN_PROGRESS"
    ACCEPTED = "ACCEPTED"
    ERROR = "ERROR"


class PayResultStatus(str, Enum):
    """Статус оплаты реестра."""

    SEND_IN_PROGRESS = "SEND_IN_PROGRESS"
    SENT = "SENT"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    PART_EXEC = "PART_EXEC"
    ERROR = "ERROR"


class PaymentResultStatus(str, Enum):
    """Статус отдельного платежа при оплате реестра."""

    IN_PROGRESS = "IN_PROGRESS"
    EXECUTED = "EXECUTED"
    SENT = "SENT"
    ERROR = "ERROR"


class PaymentInfoStatus(str, Enum):
    """Статус отдельного платежа в карточке реестра."""

    WAITING = "WAITING"
    ACCEPTED = "ACCEPTED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    DELETED = "DELETED"


class ReceiptsRequestStatus(str, Enum):
    """Статус запроса чеков по реестру."""

    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class ReceiptStatus(str, Enum):
    """Статус отдельного чека."""

    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    CANCELED = "CANCELED"
    FISCALIZE_FAILED = "FISCALIZE_FAILED"
    ERROR = "ERROR"


class RecipientStatus(str, Enum):
    """Статус карточки самозанятого."""

    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    REJECTED = "REJECTED"
    DELETED = "DELETED"
    MTNG_SCHD = "MTNG_SCHD"
    MTNG_WAIT = "MTNG_WAIT"
    MTNG_CANC = "MTNG_CANC"


class SelfEmployedStatus(str, Enum):
    """Статус самозанятости получателя."""

    REGISTRATION_WAIT = "REGISTRATION_WAIT"
    NOT_CONFIRM = "NOT_CONFIRM"
    NOT_ACTIVE = "NOT_ACTIVE"
    ACTIVE = "ACTIVE"


class SelfEmployedIdentificationStatus(str, Enum):
    """Статус идентификации самозанятого."""

    NOT_IDENTIFIED = "NOT_IDENTIFIED"
    IDENTIFIED = "IDENTIFIED"


class SelfEmployedAgreementStatus(str, Enum):
    """Статус согласия самозанятого."""

    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED = "REQUESTED"
    AGREED = "AGREED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


class PhoneType(str, Enum):
    """Тип телефона (значения на проводе — на русском)."""

    MOBILE = "Мобильный"
    HOME = "По месту жительства"
    WORK = "Рабочий"


class AddressKind(str, Enum):
    """Тип адреса анкеты (значения на проводе — на русском)."""

    RESIDENCE = "Жительства"
    REGISTRATION = "Регистрации"


class DocumentType(str, Enum):
    """Тип документа анкеты (значения на проводе — на русском)."""

    PASSPORT = "Паспорт"
    FOREIGN_PASSPORT = "Иностранный паспорт"
    FOREIGN_TRAVEL_PASSPORT = "Загр. паспорт иностранного гр."
    SERVICE_PASSPORT = "Служебный/официальный паспорт"
    DIPLOMATIC_PASSPORT = "Дипломатический паспорт"
    MIGRATION_CARD = "Миграционная карта"
    TEMPORARY_RESIDENCE_PERMIT = "Разр. на временное проживание"
    VISA = "Виза"
    RESIDENCE_PERMIT = "Вид на жительство"
