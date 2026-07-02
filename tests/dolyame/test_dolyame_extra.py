from decimal import Decimal

import httpx
import pytest

from tbank.core.errors import ServerError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.dolyame.aio import DolyameClient as AsyncDolyameClient
from tbank.dolyame.auth import DolyameAuth
from tbank.dolyame.enums import OrderStatus
from tbank.dolyame.models import (
    CommitRequest,
    CompleteDeliveryRequest,
    CorrectionRequest,
    DeliveryOrder,
    Item,
    RefundRequest,
)
from tbank.dolyame.sync import DolyameClient as SyncDolyameClient
from tbank.dolyame.webhooks import is_allowed_ip

BASE = "https://partner.dolyame.ru/v1"


def _item() -> Item:
    return Item(name="Товар", quantity=1, price=Decimal("6700.00"))


def _async(handler):
    t = AsyncTransport(
        base_url=BASE,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        auth=DolyameAuth("s", "p"),
    )
    return AsyncDolyameClient(login="s", password="p", transport=t)


def _sync(handler):
    t = SyncTransport(
        base_url=BASE,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        auth=DolyameAuth("s", "p"),
    )
    return SyncDolyameClient(login="s", password="p", transport=t)


async def test_correction_and_complete_delivery():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path.endswith("/correction"):
            return httpx.Response(200, json={"amount": 5025.00, "refund_id": "r-2"})
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "amount": 6700.0,
                "residual_amount": 0,
                "link": "u",
            },
        )

    client = _async(handler)
    ref = await client.correction(
        "order-1", CorrectionRequest(amount=Decimal("1675.00"), new_items=[_item()])
    )
    assert ref.refund_id == "r-2"
    info = await client.complete_delivery(
        "order-1",
        CompleteDeliveryRequest(
            order=DeliveryOrder(amount=Decimal("6700.00"), items=[_item()])
        ),
    )
    assert info.status is OrderStatus.COMPLETED
    assert seen == [
        "/v1/orders/order-1/correction",
        "/v1/orders/order-1/complete_delivery",
    ]
    await client.aclose()


def test_sync_full_lifecycle():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/refund"):
            return httpx.Response(200, json={"amount": 5025.0, "refund_id": "r-3"})
        if path.endswith("/correction"):
            return httpx.Response(200, json={"amount": 5025.0, "refund_id": "r-4"})
        status = "canceled" if path.endswith("/cancel") else "committed"
        return httpx.Response(
            200,
            json={
                "status": status,
                "amount": 6700.0,
                "residual_amount": 0,
                "link": "u",
            },
        )

    client = _sync(handler)
    assert client.get_order("o").status is OrderStatus.COMMITTED
    assert client.cancel("o").status is OrderStatus.CANCELED
    assert (
        client.refund(
            "o", RefundRequest(amount=Decimal("1"), returned_items=[_item()])
        ).refund_id
        == "r-3"
    )
    assert (
        client.correction("o", CorrectionRequest(amount=Decimal("1"))).refund_id
        == "r-4"
    )
    assert (
        client.commit(
            "o", CommitRequest(amount=Decimal("6700.00"), items=[_item()])
        ).status
        is OrderStatus.COMMITTED
    )
    assert (
        client.complete_delivery("o", CompleteDeliveryRequest()).status
        is OrderStatus.COMMITTED
    )
    client.close()


async def test_error_non_json_body_falls_back_to_server_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client = _async(handler)
    with pytest.raises(ServerError) as info:
        await client.get_order("x")
    assert info.value.http_status == 500
    await client.aclose()


def test_is_allowed_ip_rejects_garbage():
    assert is_allowed_ip("not-an-ip") is False
