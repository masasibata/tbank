from __future__ import annotations

from enum import Enum


class IdentificationDocumentType(str, Enum):
    """Тип документа, удостоверяющего личность контакта."""

    PASSPORT = "PASSPORT"


class PhoneType(str, Enum):
    """Тип телефона контакта."""

    MOBILE = "MOBILE"
    HOME = "HOME"
    WORK = "WORK"
    OTHER = "OTHER"
