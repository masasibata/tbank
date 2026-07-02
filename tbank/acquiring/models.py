from __future__ import annotations

from typing import Optional

from pydantic import Field

from tbank.acquiring.enums import CardStatus, CardType, PaymentStatus
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
    # "Y" — сохранить карту для рекуррента (нужен customer_key)
    recurrent: Optional[str] = None


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


# --- Рекуррентные платежи и управление клиентами/картами ---


class ChargeRequest(TBankModel):
    payment_id: str
    rebill_id: str
    ip: Optional[str] = Field(default=None, alias="IP")
    send_email: Optional[bool] = None
    info_email: Optional[str] = None


class ChargeResponse(PaymentResponse):
    pass


class AddCustomerRequest(TBankModel):
    customer_key: str
    email: Optional[str] = None
    phone: Optional[str] = None
    ip: Optional[str] = Field(default=None, alias="IP")


class CustomerRequest(TBankModel):
    """Запрос GetCustomer / RemoveCustomer."""

    customer_key: str
    ip: Optional[str] = Field(default=None, alias="IP")


class Customer(TBankModel):
    success: bool
    error_code: str
    terminal_key: Optional[str] = None
    customer_key: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None
    details: Optional[str] = None


class GetCardListRequest(TBankModel):
    customer_key: str
    saved_card: Optional[bool] = None
    ip: Optional[str] = Field(default=None, alias="IP")


class Card(TBankModel):
    card_id: str
    pan: str  # маскированный, напр. 518223******0036
    status: CardStatus
    card_type: CardType
    rebill_id: Optional[str] = None
    exp_date: Optional[str] = None  # MMYY


class RemoveCardRequest(TBankModel):
    customer_key: str
    card_id: str
    ip: Optional[str] = Field(default=None, alias="IP")


class RemoveCardResponse(TBankModel):
    success: bool
    error_code: str
    terminal_key: Optional[str] = None
    customer_key: Optional[str] = None
    card_id: Optional[str] = None
    status: Optional[CardStatus] = None
    card_type: Optional[CardType] = None
    message: Optional[str] = None
    details: Optional[str] = None
