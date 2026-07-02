import json

import httpx
import pytest

from tbank.acquiring.aio import AcquiringClient as AsyncAcquiringClient
from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.enums import CardStatus, CardType, PaymentStatus
from tbank.acquiring.models import InitRequest
from tbank.acquiring.sync import AcquiringClient as SyncAcquiringClient
from tbank.core.errors import InsufficientFundsError
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


async def test_charge_signs_request_and_parses_response():
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
                "Status": "CONFIRMED",
                "PaymentId": "700",
                "OrderId": "A-1",
                "Amount": 19200,
            },
        )

    client = _async_client(handler)
    resp = await client.charge("700", "6155312073")
    assert seen["path"] == "/v2/Charge"
    assert seen["body"]["PaymentId"] == "700"
    assert seen["body"]["RebillId"] == "6155312073"
    assert seen["body"]["TerminalKey"] == "T"
    assert "Token" in seen["body"]
    assert resp.status is PaymentStatus.CONFIRMED
    assert resp.amount == 19200
    await client.aclose()


async def test_charge_optional_fields_use_ip_alias():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"Success": True, "ErrorCode": "0", "Status": "CONFIRMED"}
        )

    client = _async_client(handler)
    await client.charge("700", "rb", ip="1.2.3.4", send_email=True, info_email="a@b.c")
    assert seen["body"]["IP"] == "1.2.3.4"  # заглавный алиас, не "Ip"
    assert seen["body"]["SendEmail"] is True
    assert seen["body"]["InfoEmail"] == "a@b.c"
    await client.aclose()


async def test_customer_lifecycle():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/AddCustomer"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "TerminalKey": "T",
                    "CustomerKey": "c1",
                },
            )
        if path.endswith("/GetCustomer"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "CustomerKey": "c1",
                    "Email": "a@b.c",
                    "Phone": "+79001234567",
                },
            )
        return httpx.Response(
            200, json={"Success": True, "ErrorCode": "0", "CustomerKey": "c1"}
        )

    client = _async_client(handler)
    assert (await client.add_customer("c1", email="a@b.c")).customer_key == "c1"
    got = await client.get_customer("c1")
    assert got.email == "a@b.c" and got.phone == "+79001234567"
    assert (await client.remove_customer("c1")).success is True
    await client.aclose()


async def test_get_card_list_parses_array():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/GetCardList"
        assert json.loads(request.content)["CustomerKey"] == "c1"
        return httpx.Response(
            200,
            json=[
                {
                    "CardId": "881900",
                    "Pan": "518223******0036",
                    "Status": "D",
                    "RebillId": "6155312073",
                    "CardType": 0,
                    "ExpDate": "1122",
                },
                {
                    "CardId": "881901",
                    "Pan": "553611******1234",
                    "Status": "A",
                    "CardType": 2,
                },
            ],
        )

    client = _async_client(handler)
    cards = await client.get_card_list("c1")
    assert len(cards) == 2
    assert cards[0].card_id == "881900"
    assert cards[0].status is CardStatus.DELETED
    assert cards[0].card_type is CardType.DEBIT
    assert cards[0].rebill_id == "6155312073"
    assert cards[1].status is CardStatus.ACTIVE
    assert cards[1].card_type is CardType.DEBIT_CREDIT
    await client.aclose()


async def test_get_card_list_error_object_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"Success": False, "ErrorCode": "1051", "Message": "нет средств"},
        )

    client = _async_client(handler)
    with pytest.raises(InsufficientFundsError):
        await client.get_card_list("c1")
    await client.aclose()


async def test_remove_card_parses_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "TerminalKey": "T",
                "CustomerKey": "c1",
                "CardId": "881900",
                "Status": "D",
                "CardType": 0,
            },
        )

    client = _async_client(handler)
    resp = await client.remove_card("c1", "881900")
    assert resp.status is CardStatus.DELETED
    assert resp.card_type is CardType.DEBIT
    await client.aclose()


async def test_init_recurrent_field():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "Status": "NEW",
                "PaymentId": "700",
                "PaymentURL": "u",
            },
        )

    client = _async_client(handler)
    await client.init(
        InitRequest(amount=19200, order_id="A-1", customer_key="c1", recurrent="Y")
    )
    assert seen["body"]["Recurrent"] == "Y"
    assert seen["body"]["CustomerKey"] == "c1"
    await client.aclose()


def test_sync_charge_and_card_list():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/Charge"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "Status": "CONFIRMED",
                    "PaymentId": "700",
                },
            )
        return httpx.Response(
            200, json=[{"CardId": "1", "Pan": "5**0", "Status": "A", "CardType": 0}]
        )

    client = _sync_client(handler)
    assert client.charge("700", "rb").status is PaymentStatus.CONFIRMED
    cards = client.get_card_list("c1")
    assert cards[0].card_id == "1"
    client.close()


def test_sync_customer_and_remove_card():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/RemoveCard"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "CardId": "1",
                    "Status": "D",
                    "CardType": 0,
                },
            )
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "CustomerKey": "c1",
                "Email": "a@b.c",
            },
        )

    client = _sync_client(handler)
    assert client.add_customer("c1", email="a@b.c").customer_key == "c1"
    assert client.get_customer("c1").email == "a@b.c"
    assert client.remove_customer("c1").success is True
    assert client.remove_card("c1", "1").status is CardStatus.DELETED
    client.close()
