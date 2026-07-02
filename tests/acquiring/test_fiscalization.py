import json

import httpx

from tbank.acquiring.aio import AcquiringClient as AsyncAcquiringClient
from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.enums import PaymentMethod, PaymentObject, Tax, Taxation
from tbank.acquiring.models import InitRequest, Payments, Receipt, ReceiptItem
from tbank.acquiring.signing import build_token
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


def _receipt() -> Receipt:
    return Receipt(
        taxation=Taxation.USN_INCOME,
        email="a@b.c",
        items=[
            ReceiptItem(
                name="Товар",
                price=100000,
                quantity=1,
                amount=100000,
                tax=Tax.VAT_22,
                payment_object=PaymentObject.COMMODITY,
                payment_method=PaymentMethod.FULL_PAYMENT,
            )
        ],
    )


async def test_init_receipt_serializes_nested_and_stays_out_of_token():
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
    await client.init(InitRequest(amount=100000, order_id="A-1", receipt=_receipt()))
    body = seen["body"]
    receipt = body["Receipt"]
    assert receipt["Taxation"] == "usn_income"
    assert receipt["Email"] == "a@b.c"
    item = receipt["Items"][0]
    assert item["Name"] == "Товар"
    assert item["Price"] == 100000
    assert item["Amount"] == 100000
    assert item["Tax"] == "vat22"
    assert item["PaymentObject"] == "commodity"
    assert item["PaymentMethod"] == "full_payment"
    # Token считается только по корневым скалярам — Receipt в подпись не входит.
    root_scalars = {"Amount": 100000, "OrderId": "A-1", "TerminalKey": "T"}
    assert body["Token"] == build_token(root_scalars, "p")
    await client.aclose()


async def test_receipt_with_payments_and_no_vat():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"Success": True, "ErrorCode": "0", "Status": "NEW"}
        )

    client = _async_client(handler)
    receipt = Receipt(
        taxation=Taxation.OSN,
        phone="+79001234567",
        items=[
            ReceiptItem(name="X", price=5000, quantity=2, amount=10000, tax=Tax.NONE)
        ],
        payments=Payments(electronic=10000, cash=0),
    )
    await client.init(InitRequest(amount=10000, order_id="A-2", receipt=receipt))
    receipt_body = seen["body"]["Receipt"]
    assert receipt_body["Payments"]["Electronic"] == 10000
    assert receipt_body["Phone"] == "+79001234567"
    assert receipt_body["Items"][0]["Tax"] == "none"
    await client.aclose()


async def test_send_closing_receipt():
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
                "PaymentId": "700",
            },
        )

    client = _async_client(handler)
    resp = await client.send_closing_receipt("700", _receipt())
    assert seen["path"] == "/v2/SendClosingReceipt"
    assert seen["body"]["PaymentId"] == "700"
    assert seen["body"]["Receipt"]["Items"][0]["Name"] == "Товар"
    assert "Token" in seen["body"]
    assert resp.success is True
    await client.aclose()


async def test_charge_with_receipt():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"Success": True, "ErrorCode": "0", "Status": "CONFIRMED"}
        )

    client = _async_client(handler)
    await client.charge("700", "rb", receipt=_receipt())
    assert seen["body"]["Receipt"]["Taxation"] == "usn_income"
    await client.aclose()


def test_sync_init_with_receipt():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"Success": True, "ErrorCode": "0", "Status": "NEW"}
        )

    client = _sync_client(handler)
    client.init(InitRequest(amount=100000, order_id="A-3", receipt=_receipt()))
    assert seen["body"]["Receipt"]["Items"][0]["Price"] == 100000
    client.close()


def test_sync_send_closing_receipt_and_charge_with_receipt():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"Success": True, "ErrorCode": "0", "Status": "CONFIRMED"}
        )

    client = _sync_client(handler)
    assert client.send_closing_receipt("700", _receipt()).success is True
    assert client.charge("700", "rb", receipt=_receipt()).success is True
    client.close()
