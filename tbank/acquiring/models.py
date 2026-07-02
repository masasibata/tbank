from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from tbank.acquiring.enums import (
    AccountQrStatus,
    CardStatus,
    CardType,
    PaymentStatus,
    QrDataType,
)
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


# --- СБП / QR ---


class GetQrRequest(TBankModel):
    payment_id: str
    data_type: Optional[QrDataType] = None  # PAYLOAD (default) | IMAGE
    bank_id: Optional[str] = None  # id банка из QrMembersList → deeplink


class GetQrResponse(TBankModel):
    success: bool
    error_code: str
    terminal_key: Optional[str] = None
    order_id: Optional[str] = None
    data: Optional[str] = None  # payload-ссылка (qr.nspk.ru) или SVG
    payment_id: Optional[str] = None
    request_key: Optional[str] = None
    message: Optional[str] = None
    details: Optional[str] = None


class QrMembersListRequest(TBankModel):
    payment_id: str


class QrMember(TBankModel):
    member_id: Optional[str] = None  # = BankId для GetQr/AddAccountQr
    member_name: Optional[str] = None
    is_payee: Optional[bool] = None


class QrMembersListResponse(TBankModel):
    success: bool
    error_code: str
    terminal_key: Optional[str] = None
    order_id: Optional[str] = None
    members: List[QrMember] = Field(default_factory=list)
    message: Optional[str] = None
    details: Optional[str] = None


class AddAccountQrRequest(TBankModel):
    description: str
    data_type: Optional[QrDataType] = None
    bank_id: Optional[str] = None
    redirect_due_date: Optional[str] = None


class AddAccountQrResponse(TBankModel):
    success: bool
    error_code: str
    terminal_key: Optional[str] = None
    data: Optional[str] = None  # QR для привязки
    request_key: Optional[str] = None
    message: Optional[str] = None
    details: Optional[str] = None


class GetAddAccountQrStateRequest(TBankModel):
    request_key: str


class AddAccountQrState(TBankModel):
    success: bool
    error_code: str
    terminal_key: Optional[str] = None
    request_key: Optional[str] = None
    account_token: Optional[str] = None  # токен привязки для ChargeQr
    bank_member_id: Optional[str] = None
    bank_member_name: Optional[str] = None
    status: Optional[AccountQrStatus] = None
    message: Optional[str] = None
    details: Optional[str] = None


class ChargeQrRequest(TBankModel):
    payment_id: str
    account_token: str
    ip: Optional[str] = Field(default=None, alias="IP")
    send_email: Optional[bool] = None
    info_email: Optional[str] = None
    bank_member_id: Optional[str] = None


class ChargeQrResponse(PaymentResponse):
    currency: Optional[int] = None
