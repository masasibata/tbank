from __future__ import annotations

from enum import Enum, IntEnum


class ContractSubject(IntEnum):
    """Предмет валютного контракта."""

    GOODS = 0
    SERVICES = 1
    GOODS_AND_SERVICES = 2
    CREDITS_AND_LEASING = 3
    ESTATE_SALE = 4
    INVESTMENTS = 5
    NON_FINANCIAL = 6


class ContractType(IntEnum):
    """Тип валютного контракта."""

    EXPORT = 0
    IMPORT = 1
    MIXED = 2


class Supply(IntEnum):
    """Условие поставки товара."""

    CROSSES_BORDER = 0
    TRANSIT = 1
    NO_BORDER = 2


class EstateType(IntEnum):
    """Тип недвижимости в контракте."""

    ESTATE = 0
    VESSELS = 1


class SignAffiliation(str, Enum):
    """Признак аффилированности контрагента."""

    YES = "YES"
    NO = "NO"


class ApplicationStatus(str, Enum):
    """Статус заявления по валютному контракту."""

    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    SUBMITTED = "SUBMITTED"
