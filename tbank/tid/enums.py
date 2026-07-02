from __future__ import annotations

from enum import Enum


class AddressType(str, Enum):
    """Тип адреса физлица."""

    RESIDENCE = "RESIDENCE_ADDRESS"
    REGISTRATION = "REGISTRATION_ADDRESS"
    WORK = "WORK_ADDRESS"
    DELIVERY = "DELIVERY_ADDRESS"


class IdDocumentType(str, Enum):
    """Тип документа, удостоверяющего личность."""

    PASSPORT = "PASSPORT"
    FOREIGN_PASSPORT = "FOREIGN_PASSPORT"
    FOREIGN_INTERNATIONAL_PASSPORT = "FOREIGN_INTERNATIONAL_PASSPORT"
    RF_INTERNATIONAL_PASSPORT = "RF_INTERNATIONAL_PASSPORT"
    BIRTH_CERTIFICATE = "BIRTH_CERTIFICATE"
    RF_RESIDENCE_PERMIT = "RF_RESIDENCE_PERMIT"


class DocumentCheckStatus(str, Enum):
    """Результат проверки документа при удалённой идентификации."""

    NOT_CHECKED = "NOT_CHECKED"
    VALID = "VALID"
    INVALID = "INVALID"


class IdentificationResult(str, Enum):
    """Итог удалённой идентификации."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class TaxationScheme(str, Enum):
    """Система налогообложения компании."""

    USN_INCOMES = "USN_INCOMES"
    USN_INCOMES_MINUS_EXPENSES = "USN_INCOMES_MINUS_EXPENSES"
    AUSN_INCOMES_MINUS_EXPENSES = "AUSN_INCOMES_MINUS_EXPENSES"
    AUSN_INCOMES = "AUSN_INCOMES"
    OSNO = "OSNO"
    NPD = "NPD"
    ESHN = "ESHN"
    ENVD = "ENVD"


class LegalStatus(str, Enum):
    """Правовой статус компании."""

    ACTIVE = "active"
    LIQUIDATING = "liquidating"
    LIQUIDATED = "liquidated"
    BANKRUPTING = "bankrupting"
    BANKRUPTED = "bankrupted"
    UNKNOWN = "unknown"


class Grade(str, Enum):
    """Грейд клиента (уровень программы привилегий)."""

    NONE = "NONE"
    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"
    FOURTH = "FOURTH"


class CounterRepeatability(str, Enum):
    """Периодичность обнуления счётчика услуги."""

    MONTH = "MONTH"
    YEAR = "YEAR"


class BundleCode(str, Enum):
    """Тип активной подписки."""

    PRO = "PRO"
    PREMIUM = "PREMIUM"
    PRIVATE = "PRIVATE"
    TEAM_PRO = "TEAM_PRO"
    TEAM_SELECT = "TEAM_SELECT"
    TEAM_PREMIUM = "TEAM_PREMIUM"
    TEAM_PRIVATE = "TEAM_PRIVATE"
    DEFAULT = "DEFAULT"


class CardType(str, Enum):
    """Тип карты — кредитная или дебетовая."""

    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class GrantType(str, Enum):
    """Тип OAuth 2.0 grant при обмене на токен."""

    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"


class TokenTypeHint(str, Enum):
    """Подсказка серверу о типе отзываемого токена (RFC 7009)."""

    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
