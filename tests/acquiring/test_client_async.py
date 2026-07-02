import json

import httpx
import pytest

from tbank.acquiring.aio import AcquiringClient
from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.models import InitRequest
from tbank.core.errors import InsufficientFundsError
from tbank.core.transport import AsyncTransport


def _client(handler):
    transport = AsyncTransport(
        base_url="https://securepay.tinkoff.ru/v2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        auth=TokenSignatureAuth("T", "p"),
    )
    return AcquiringClient(terminal_key="T", password="p", transport=transport)


async def test_init_signs_request_and_returns_payment_url():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "PaymentId": "700",
                "Status": "NEW",
                "PaymentURL": "http://pay",
            },
        )

    client = _client(handler)
    resp = await client.init(InitRequest(amount=19200, order_id="A-1"))
    assert seen["path"] == "/v2/Init"
    assert seen["body"]["TerminalKey"] == "T"
    assert "Token" in seen["body"]
    assert resp.payment_url == "http://pay"
    await client.aclose()


async def test_init_raises_on_error_code():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"Success": False, "ErrorCode": "1051", "Message": "нет средств"},
        )

    client = _client(handler)
    with pytest.raises(InsufficientFundsError):
        await client.init(InitRequest(amount=100, order_id="A-1"))
    await client.aclose()


async def test_get_state_confirm_cancel_paths():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "PaymentId": "700",
                "Status": "CONFIRMED",
            },
        )

    client = _client(handler)
    await client.get_state("700")
    await client.confirm("700")
    await client.cancel("700", amount=100)
    assert seen == ["/v2/GetState", "/v2/Confirm", "/v2/Cancel"]
    await client.aclose()
