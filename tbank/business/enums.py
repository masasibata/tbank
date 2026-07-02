from __future__ import annotations

from enum import Enum


class AccountType(str, Enum):
    CURRENT = "Current"
    TAX = "Tax"
    TENDER = "Tender"
    OVERNIGHT = "Overnight"


class OperationStatus(str, Enum):
    ALL = "All"
    AUTHORIZATION = "Authorization"
    TRANSACTION = "Transaction"


class TypeOfOperation(str, Enum):
    CREDIT = "Credit"
    DEBIT = "Debit"


class PaymentStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
