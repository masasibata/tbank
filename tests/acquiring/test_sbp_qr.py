import json

import httpx

from tbank.acquiring.aio import AcquiringClient as AsyncAcquiringClient
from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.enums import AccountQrStatus, PaymentStatus, QrDataType
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


async def test_get_qr_signs_and_returns_payload():
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
                "OrderId": "A-1",
                "Data": "https://qr.nspk.ru/AS1",
                "PaymentId": "700",
            },
        )

    client = _async_client(handler)
    resp = await client.get_qr("700", data_type=QrDataType.PAYLOAD)
    assert seen["path"] == "/v2/GetQr"
    assert seen["body"]["PaymentId"] == "700"
    assert seen["body"]["DataType"] == "PAYLOAD"
    assert "Token" in seen["body"]
    assert resp.data == "https://qr.nspk.ru/AS1"
    await client.aclose()


async def test_get_qr_image_with_bank_id():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"Success": True, "ErrorCode": "0", "Data": "<svg/>"}
        )

    client = _async_client(handler)
    await client.get_qr("700", data_type=QrDataType.IMAGE, bank_id="uuid-1")
    assert seen["body"]["DataType"] == "IMAGE"
    assert seen["body"]["BankId"] == "uuid-1"
    await client.aclose()


async def test_get_qr_members_parses_array():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/QrMembersList"
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "TerminalKey": "T",
                "OrderId": "A-1",
                "Members": [
                    {
                        "MemberId": "100000000004",
                        "MemberName": "Т-Банк",
                        "IsPayee": True,
                    },
                    {
                        "MemberId": "100000000005",
                        "MemberName": "Сбербанк",
                        "IsPayee": False,
                    },
                ],
            },
        )

    client = _async_client(handler)
    resp = await client.get_qr_members("700")
    assert len(resp.members) == 2
    assert resp.members[0].member_id == "100000000004"
    assert resp.members[0].is_payee is True
    assert resp.members[1].member_name == "Сбербанк"
    await client.aclose()


async def test_add_account_qr_and_state():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/AddAccountQr"):
            assert json.loads(request.content)["Description"] == "Привязка"
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "TerminalKey": "T",
                    "Data": "https://qr.nspk.ru/AS2",
                    "RequestKey": "rk-1",
                },
            )
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "RequestKey": "rk-1",
                "AccountToken": "at-1",
                "BankMemberId": "100000000004",
                "Status": "ACTIVE",
            },
        )

    client = _async_client(handler)
    add = await client.add_account_qr("Привязка")
    assert add.request_key == "rk-1"
    assert add.data == "https://qr.nspk.ru/AS2"
    state = await client.get_add_account_qr_state("rk-1")
    assert state.account_token == "at-1"
    assert state.status is AccountQrStatus.ACTIVE
    await client.aclose()


async def test_charge_qr_signs_and_parses():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "Status": "CONFIRMED",
                "PaymentId": "701",
                "Amount": 19200,
                "OrderId": "A-2",
            },
        )

    client = _async_client(handler)
    resp = await client.charge_qr("701", "at-1", ip="1.2.3.4")
    assert seen["path"] == "/v2/ChargeQr"
    assert seen["body"]["PaymentId"] == "701"
    assert seen["body"]["AccountToken"] == "at-1"
    assert seen["body"]["IP"] == "1.2.3.4"
    assert resp.status is PaymentStatus.CONFIRMED
    assert resp.amount == 19200
    await client.aclose()


def test_sync_get_qr_and_charge_qr():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/GetQr"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "Data": "https://qr.nspk.ru/X",
                },
            )
        return httpx.Response(
            200, json={"Success": True, "ErrorCode": "0", "Status": "CONFIRMED"}
        )

    client = _sync_client(handler)
    assert client.get_qr("700").data == "https://qr.nspk.ru/X"
    assert client.charge_qr("701", "at-1").status is PaymentStatus.CONFIRMED
    client.close()


def test_sync_members_and_account_binding():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/QrMembersList"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "Members": [{"MemberId": "1", "MemberName": "Т-Банк"}],
                },
            )
        if path.endswith("/AddAccountQr"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "Data": "u",
                    "RequestKey": "rk",
                },
            )
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "AccountToken": "at",
                "Status": "ACTIVE",
            },
        )

    client = _sync_client(handler)
    assert client.get_qr_members("700").members[0].member_id == "1"
    assert client.add_account_qr("Привязка").request_key == "rk"
    assert client.get_add_account_qr_state("rk").status is AccountQrStatus.ACTIVE
    client.close()
