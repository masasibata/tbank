from __future__ import annotations

from enum import Enum


class RegistryCreateType(str, Enum):
    """Поведение при ошибках в платежах реестра."""

    IGNORE_ERRORS = "IGNORE_ERRORS"
    FAIL_ERRORS = "FAIL_ERRORS"


class RevenueTypeCode(str, Enum):
    """Код вида выплаты (1–5)."""

    CODE_1 = "1"
    CODE_2 = "2"
    CODE_3 = "3"
    CODE_4 = "4"
    CODE_5 = "5"


class DraftStatus(str, Enum):
    """Статус черновика (анкеты сотрудника / реестра) в async-результате."""

    QUEUED = "QUEUED"
    CREATED = "CREATED"
    ERROR = "ERROR"


class SubmitResultStatus(str, Enum):
    """Статус подписания (или создания-и-подписания) реестра."""

    IN_PROGRESS = "IN_PROGRESS"
    ACCEPTED = "ACCEPTED"
    ERROR = "ERROR"


class CancelStatus(str, Enum):
    """Статус отмены отправки реестра."""

    QUEUED = "QUEUED"
    DONE = "DONE"
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


class PaymentInfoStatus(str, Enum):
    """Статус отдельного платежа в карточке реестра."""

    WAITING = "WAITING"
    ACCEPTED = "ACCEPTED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    DELETED = "DELETED"


class EmployeeStatus(str, Enum):
    """Статус карточки сотрудника."""

    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    REJECTED = "REJECTED"
    FIRED = "FIRED"
    DELETED = "DELETED"
    MTNG_SCHD = "MTNG_SCHD"
    MTNG_WAIT = "MTNG_WAIT"
    MTNG_CANC = "MTNG_CANC"


class PhoneType(str, Enum):
    """Тип телефона (значения на проводе — на русском)."""

    MOBILE = "Мобильный"
    HOME = "По месту жительства"
    WORK = "Рабочий"


class AddressKind(str, Enum):
    """Тип адреса анкеты (значения на проводе — на русском)."""

    RESIDENCE = "Жительства"
    REGISTRATION = "Регистрации"
    WORK = "Работы"


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
