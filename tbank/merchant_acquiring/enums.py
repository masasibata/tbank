from __future__ import annotations

from enum import Enum


class OperationType(str, Enum):
    """Тип операции по терминалу торгового эквайринга."""

    DEBIT = "Debit"
    CREDIT = "Credit"
    OTHER = "Other"
