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


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    EXECUTED = "EXECUTED"


class InvoiceVat(str, Enum):
    NONE = "None"  # без НДС
    VAT_0 = "0"
    VAT_5 = "5"
    VAT_7 = "7"
    VAT_10 = "10"
    VAT_18 = "18"
    VAT_20 = "20"
    VAT_22 = "22"


class SbpVat(str, Enum):
    VAT_0 = "0"
    VAT_5 = "5"
    VAT_7 = "7"
    VAT_10 = "10"
    VAT_20 = "20"
    VAT_22 = "22"


class SbpQrType(str, Enum):
    ONETIME = "Onetime"
    REUSABLE = "Reusable"


class SbpQrStatus(str, Enum):
    READY = "Ready"
    PAID = "Paid"
    CANCELLED = "Cancelled"
    EXPIRED = "Expired"
    FAILED = "Failed"
