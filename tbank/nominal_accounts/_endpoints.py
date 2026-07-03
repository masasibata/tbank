"""Пути и парсеры номинальных счетов (общие для sync- и aio-клиентов)."""

from __future__ import annotations

from pydantic import TypeAdapter

from tbank.nominal_accounts.models import (
    AddCardRequestResponse,
    BankDetailsResponse,
    BeneficiaryResponse,
    PaymentResponse,
)

NA = "/api/v1/nominal-accounts"
NA_V2 = "/api/v2/nominal-accounts"

# Ответы-полиморфы (oneOf) валидируются через TypeAdapter по дискриминатору.
BENEFICIARY: TypeAdapter[BeneficiaryResponse] = TypeAdapter(BeneficiaryResponse)
ADD_CARD: TypeAdapter[AddCardRequestResponse] = TypeAdapter(AddCardRequestResponse)
BANK_DETAILS: TypeAdapter[BankDetailsResponse] = TypeAdapter(BankDetailsResponse)
PAYMENT: TypeAdapter[PaymentResponse] = TypeAdapter(PaymentResponse)
