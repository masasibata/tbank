from __future__ import annotations

from enum import Enum


class OrderStatus(str, Enum):
    NEW = "new"
    APPROVED = "approved"  # одобрен, ждём оплату первой части
    WAIT_FOR_COMMIT = "wait_for_commit"  # холд, ждём подтверждения магазином
    COMMITTED = "committed"  # магазин подтвердил
    COMPLETED = "completed"  # первый платёж прошёл
    REJECTED = "rejected"
    CANCELED = "canceled"


class ScheduleStatus(str, Enum):
    SCHEDULED = "scheduled"
    HOLD = "hold"
    PAID = "paid"


class RefundStatus(str, Enum):
    PENDING = "pending"  # в обработке
    PROCESSED = "processed"  # деньги возвращены
