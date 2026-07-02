from __future__ import annotations

from typing import Optional

from pydantic import Field

from tbank.acquiring.enums import PaymentStatus
from tbank.core.models import Kopecks, TBankModel


class InitRequest(TBankModel):
    amount: Kopecks
    order_id: str
    description: Optional[str] = None
    customer_key: Optional[str] = None
    success_url: Optional[str] = Field(default=None, alias="SuccessURL")
    fail_url: Optional[str] = Field(default=None, alias="FailURL")
    notification_url: Optional[str] = Field(default=None, alias="NotificationURL")
    redirect_due_date: Optional[str] = None
    pay_type: Optional[str] = None


class PaymentResponse(TBankModel):
    success: bool
    error_code: str
    terminal_key: Optional[str] = None
    status: Optional[PaymentStatus] = None
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: Optional[Kopecks] = None
    message: Optional[str] = None
    details: Optional[str] = None


class InitResponse(PaymentResponse):
    payment_url: Optional[str] = Field(default=None, alias="PaymentURL")


class GetStateRequest(TBankModel):
    payment_id: str


class GetStateResponse(PaymentResponse):
    pass


class ConfirmRequest(TBankModel):
    payment_id: str
    amount: Optional[Kopecks] = None


class ConfirmResponse(PaymentResponse):
    pass


class CancelRequest(TBankModel):
    payment_id: str
    amount: Optional[Kopecks] = None


class CancelResponse(PaymentResponse):
    original_amount: Optional[Kopecks] = None
    new_amount: Optional[Kopecks] = None
