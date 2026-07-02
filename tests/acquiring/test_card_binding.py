import json

import httpx

from tbank.acquiring.aio import AcquiringClient as AsyncAcquiringClient
from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.enums import AddCardStatus, CheckType
from tbank.acquiring.sync import AcquiringClient as SyncAcquiringClient
from tbank.core.transport import AsyncTransport, SyncTransport


def _async_client(handler):
    transport = AsyncTransport(
        base_url="https://securepay.tinkoff.ru/v2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        auth=TokenSignatureAuth("T", "p"),
    )
    return AsyncAcquiringClient(terminal_key="T", password="p", transport=transport)


def _sync_client(handler):
    transport = SyncTransport(
        base_url="https://securepay.tinkoff.ru/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        auth=TokenSignatureAuth("T", "p"),
    )
    return SyncAcquiringClient(terminal_key="T", password="p", transport=transport)


async def test_add_card_signs_and_returns_payment_url():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "TerminalKey": "T",
                "CustomerKey": "c1",
                "RequestKey": "rk-1",
                "PaymentURL": "https://sec/bind",
            },
        )

    client = _async_client(handler)
    resp = await client.add_card(
        "c1", check_type=CheckType.THREE_DS, ip="1.2.3.4", resident_state=True
    )
    assert seen["path"] == "/v2/AddCard"
    assert seen["body"]["CustomerKey"] == "c1"
    assert seen["body"]["CheckType"] == "3DS"
    assert seen["body"]["IP"] == "1.2.3.4"
    assert seen["body"]["ResidentState"] is True
    assert "Token" in seen["body"]
    assert resp.request_key == "rk-1"
    assert resp.payment_url == "https://sec/bind"
    await client.aclose()


async def test_get_add_card_state_parses_status():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/GetAddCardState"
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "RequestKey": "rk-1",
                "CustomerKey": "c1",
                "Status": "COMPLETED",
                "CardId": "881900",
                "RebillId": "6155312073",
            },
        )

    client = _async_client(handler)
    state = await client.get_add_card_state("rk-1")
    assert state.status is AddCardStatus.COMPLETED
    assert state.card_id == "881900"
    assert state.rebill_id == "6155312073"
    await client.aclose()


async def test_get_qr_state_parses_refund():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/GetQrState"
        assert json.loads(request.content)["PaymentId"] == "700"
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "Status": "REFUNDED",
                "OrderId": "A-1",
                "Amount": 19200,
            },
        )

    client = _async_client(handler)
    st = await client.get_qr_state("700")
    assert st.status == "REFUNDED"
    assert st.amount == 19200
    await client.aclose()


def test_sync_card_binding_and_qr_state():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/AddCard"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "RequestKey": "rk",
                    "PaymentURL": "u",
                },
            )
        if path.endswith("/GetAddCardState"):
            return httpx.Response(
                200, json={"Success": True, "ErrorCode": "0", "Status": "NEW"}
            )
        return httpx.Response(
            200, json={"Success": True, "ErrorCode": "0", "Status": "REFUNDING"}
        )

    client = _sync_client(handler)
    assert client.add_card("c1").request_key == "rk"
    assert client.get_add_card_state("rk").status is AddCardStatus.NEW
    assert client.get_qr_state("700").status == "REFUNDING"
    client.close()
