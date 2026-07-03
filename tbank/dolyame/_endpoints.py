"""Хост и пути API «Долями» (общие для sync- и aio-клиентов)."""

from __future__ import annotations

PROD_URL = "https://partner.dolyame.ru/v1"

CREATE_ORDER = "/orders/create"


def order_info_path(order_id: str) -> str:
    return f"/orders/{order_id}/info"


def commit_path(order_id: str) -> str:
    return f"/orders/{order_id}/commit"


def cancel_path(order_id: str) -> str:
    return f"/orders/{order_id}/cancel"


def refund_path(order_id: str) -> str:
    return f"/orders/{order_id}/refund"


def correction_path(order_id: str) -> str:
    return f"/orders/{order_id}/correction"


def complete_delivery_path(order_id: str) -> str:
    return f"/orders/{order_id}/complete_delivery"
