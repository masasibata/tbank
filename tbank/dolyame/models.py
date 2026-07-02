from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from tbank.dolyame.enums import OrderStatus, RefundStatus, ScheduleStatus


class DolyameModel(BaseModel):
    """База Долями: провод — snake_case (совпадает с Python), без алиасов."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


# Суммы Долями — рубли, в JSON число (double, 2 знака); у пользователя Decimal.
Money = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


# --- Общие ---


class Item(DolyameModel):
    name: str
    quantity: int
    price: Money  # цена одной позиции, рубли
    sku: Optional[str] = None


class ClientInfo(DolyameModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    birthdate: Optional[date] = None  # yyyy-MM-dd
    phone: Optional[str] = None  # +79993334444
    email: Optional[str] = None


# --- Запросы ---


class Order(DolyameModel):
    id: str  # идентификатор заказа в системе магазина
    amount: Money  # amount + prepaid_amount = Σ(qty × price)
    items: List[Item]
    prepaid_amount: Optional[Money] = None  # аванс иными способами


class CreateOrderRequest(DolyameModel):
    order: Order
    client_info: Optional[ClientInfo] = None  # на верхнем уровне, не внутри order
    notification_url: Optional[str] = None
    success_url: Optional[str] = None
    fail_url: Optional[str] = None


class CommitRequest(DolyameModel):
    amount: Money
    items: List[Item]
    prepaid_amount: Optional[Money] = None


class RefundRequest(DolyameModel):
    amount: Money
    returned_items: List[Item]
    refunded_prepaid_amount: Optional[Money] = None


class CorrectionRequest(DolyameModel):
    amount: Money
    refunded_prepaid_amount: Optional[Money] = None
    new_items: Optional[List[Item]] = None  # перезаписать корзину


class DeliveryOrder(DolyameModel):
    amount: Money
    items: List[Item]
    prepaid_amount: Optional[Money] = None


class CompleteDeliveryRequest(DolyameModel):
    order: Optional[DeliveryOrder] = None


# --- Ответы ---


class ScheduleItem(DolyameModel):
    amount: Money
    payment_date: date
    status: ScheduleStatus


class RefundInfoItem(DolyameModel):
    refund_id: str
    refunded_amount: Money
    refunded_prepaid_amount: Money
    status: RefundStatus


class RefundInfo(DolyameModel):
    total_refunded_amount: Money
    total_refunded_prepaid_amount: Money
    items: List[RefundInfoItem] = Field(default_factory=list)


class InstallmentInfo(DolyameModel):
    term: int
    loan_number: Optional[str] = None


class OrderInfoItem(DolyameModel):
    name: str
    price: Money
    quantity: int
    sku: Optional[str] = None


class OrderInfo(DolyameModel):
    status: OrderStatus
    amount: Money  # общая сумма к оплате клиентом
    residual_amount: Money  # остаток к погашению клиентом
    link: str  # ссылка на форму заказа (payment_url)
    payment_schedule: List[ScheduleItem] = Field(default_factory=list)
    refund_info: Optional[RefundInfo] = None
    installment_info: Optional[InstallmentInfo] = None
    items: Optional[List[OrderInfoItem]] = None  # только в методе info
    end_cooling_period: Optional[datetime] = None


class RefundResponse(DolyameModel):
    amount: Money  # сумма к выплате клиентом после возврата
    refund_id: str


class WebhookNotification(DolyameModel):
    id: str
    status: OrderStatus
    amount: Optional[Money] = None
    residual_amount: Optional[Money] = None
    demo: Optional[bool] = None
    client_info: Optional[ClientInfo] = None
    payment_schedule: List[ScheduleItem] = Field(default_factory=list)
    cid: Optional[str] = None
    signature: Optional[str] = None
