from __future__ import annotations

from typing import Any, Dict, Optional

from tbank.acquiring.enums import PaymentStatus
from tbank.acquiring.signing import build_token
from tbank.core.models import Kopecks, TBankModel


class PaymentNotification(TBankModel):
    terminal_key: str
    order_id: str
    success: bool
    status: PaymentStatus
    payment_id: int
    error_code: str
    amount: Optional[Kopecks] = None
    card_id: Optional[int] = None
    pan: Optional[str] = None
    exp_date: Optional[str] = None
    rebill_id: Optional[int] = None
    token: str


def parse_notification(data: Dict[str, Any]) -> PaymentNotification:
    """Разобрать входящую нотификацию эквайринга в типизированную модель."""
    return PaymentNotification.model_validate(data)


def verify_notification(data: Dict[str, Any], password: str) -> bool:
    """Проверить подпись нотификации (тот же алгоритм Token по корневым полям)."""
    received = str(data.get("Token", ""))
    expected = build_token(data, password)
    return bool(received) and received == expected
