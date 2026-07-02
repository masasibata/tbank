import json
from decimal import Decimal

import httpx
import pytest

from tbank.core.errors import InvalidRequestError, ValidationError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.dolyame.aio import DolyameClient as AsyncDolyameClient
from tbank.dolyame.auth import DolyameAuth
from tbank.dolyame.enums import OrderStatus, ScheduleStatus
from tbank.dolyame.models import (
    ClientInfo,
    CommitRequest,
    CreateOrderRequest,
    Item,
    Order,
    RefundRequest,
)
from tbank.dolyame.sync import DolyameClient as SyncDolyameClient


def _async_client(handler):
    transport = AsyncTransport(
        base_url="https://partner.dolyame.ru/v1",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        auth=DolyameAuth("shop", "secret"),
    )
    return AsyncDolyameClient(login="shop", password="secret", transport=transport)


def _order_request() -> CreateOrderRequest:
    return CreateOrderRequest(
        order=Order(
            id="order-1",
            amount=Decimal("6700.00"),
            items=[Item(name="Товар", quantity=1, price=Decimal("6700.00"))],
        ),
        client_info=ClientInfo(first_name="Иван", phone="+79993334444"),
        notification_url="https://shop/webhook",
    )


async def test_create_order_serializes_body_and_auth():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("Authorization")
        seen["corr"] = request.headers.get("X-Correlation-ID")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "status": "new",
                "amount": 6700.00,
                "residual_amount": 6700.00,
                "link": "https://dolyame.ru/order/xxx",
                "payment_schedule": [
                    {
                        "amount": 1675.00,
                        "payment_date": "2026-01-15",
                        "status": "scheduled",
                    }
                ],
            },
        )

    client = _async_client(handler)
    info = await client.create_order(_order_request())
    assert seen["path"] == "/v1/orders/create"
    assert seen["auth"].startswith("Basic ")
    assert len(seen["corr"]) == 36  # UUID v4
    body = seen["body"]
    assert body["order"]["id"] == "order-1"
    assert body["order"]["amount"] == 6700.0 and isinstance(
        body["order"]["amount"], float
    )
    assert body["order"]["items"][0]["price"] == 6700.0
    assert body["client_info"]["first_name"] == "Иван"  # на верхнем уровне
    assert "client_info" not in body["order"]  # не внутри order
    assert info.status is OrderStatus.NEW
    assert info.residual_amount == Decimal("6700.00")
    assert info.link.startswith("https://dolyame.ru")
    assert info.payment_schedule[0].status is ScheduleStatus.SCHEDULED
    await client.aclose()


async def test_get_order_parses_status_and_items():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/orders/order-1/info"
        return httpx.Response(
            200,
            json={
                "status": "committed",
                "amount": 6700.00,
                "residual_amount": 5025.00,
                "link": "u",
                "items": [{"name": "Товар", "price": 6700.00, "quantity": 1}],
            },
        )

    client = _async_client(handler)
    info = await client.get_order("order-1")
    assert info.status is OrderStatus.COMMITTED
    assert info.residual_amount == Decimal("5025.00")
    assert info.items[0].name == "Товар"
    await client.aclose()


async def test_cancel_sends_no_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["content"] = request.content
        return httpx.Response(
            200,
            json={
                "status": "canceled",
                "amount": 6700.0,
                "residual_amount": 0,
                "link": "u",
            },
        )

    client = _async_client(handler)
    info = await client.cancel("order-1")
    assert seen["path"] == "/v1/orders/order-1/cancel"
    assert seen["content"] == b""  # тело не передаётся
    assert info.status is OrderStatus.CANCELED
    await client.aclose()


async def test_refund_returns_refund_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/orders/order-1/refund"
        body = json.loads(request.content)
        assert body["amount"] == 1675.0
        assert body["returned_items"][0]["name"] == "Товар"
        return httpx.Response(200, json={"amount": 5025.00, "refund_id": "r-1"})

    client = _async_client(handler)
    resp = await client.refund(
        "order-1",
        RefundRequest(
            amount=Decimal("1675.00"),
            returned_items=[Item(name="Товар", quantity=1, price=Decimal("1675.00"))],
        ),
    )
    assert resp.refund_id == "r-1"
    assert resp.amount == Decimal("5025.00")
    await client.aclose()


async def test_error_422_validation():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "code": "UNPROCESSABLE_ENTITY",
                "errorDetailCode": "NOT_ENOUGH_MONEY",
                "message": "нет средств",
                "correlationId": "corr-1",
            },
        )

    client = _async_client(handler)
    with pytest.raises(ValidationError) as info:
        await client.get_order("x")
    assert info.value.code == "UNPROCESSABLE_ENTITY"
    assert info.value.details == "NOT_ENOUGH_MONEY"
    assert info.value.http_status == 422
    assert info.value.error_id == "corr-1"
    await client.aclose()


async def test_error_404_maps_to_invalid_request():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"code": "NOT_FOUND", "message": "нет"})

    client = _async_client(handler)
    with pytest.raises(InvalidRequestError):
        await client.get_order("x")
    await client.aclose()


def test_cert_required_without_transport():
    with pytest.raises(ValueError):
        AsyncDolyameClient(login="shop", password="secret")  # ни cert, ни transport


def test_webhook_parse_and_ip_allowlist():
    from tbank.dolyame.webhooks import is_allowed_ip, parse_notification

    note = parse_notification(
        {
            "id": "order-1",
            "status": "committed",
            "amount": 6700.0,
            "demo": True,
            "cid": "n-1",
        }
    )
    assert note.status is OrderStatus.COMMITTED
    assert note.demo is True
    assert is_allowed_ip("91.194.226.10") is True
    assert is_allowed_ip("8.8.8.8") is False


def test_sync_create_and_commit():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/commit"):
            return httpx.Response(
                200,
                json={
                    "status": "committed",
                    "amount": 6700.0,
                    "residual_amount": 5025.0,
                    "link": "u",
                },
            )
        return httpx.Response(
            200,
            json={
                "status": "new",
                "amount": 6700.0,
                "residual_amount": 6700.0,
                "link": "u",
            },
        )

    transport = SyncTransport(
        base_url="https://partner.dolyame.ru/v1",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        auth=DolyameAuth("s", "p"),
    )
    client = SyncDolyameClient(login="s", password="p", transport=transport)
    assert client.create_order(_order_request()).status is OrderStatus.NEW
    committed = client.commit(
        "order-1",
        CommitRequest(
            amount=Decimal("6700.00"),
            items=[Item(name="Товар", quantity=1, price=Decimal("6700.00"))],
        ),
    )
    assert committed.status is OrderStatus.COMMITTED
    client.close()
