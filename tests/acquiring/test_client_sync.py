import httpx
import pytest

from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.models import InitRequest
from tbank.acquiring.sync import AcquiringClient
from tbank.core.errors import InsufficientFundsError
from tbank.core.transport import SyncTransport


def _client(handler):
    transport = SyncTransport(
        base_url="https://securepay.tinkoff.ru/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        auth=TokenSignatureAuth("T", "p"),
    )
    return AcquiringClient(terminal_key="T", password="p", transport=transport)


def test_sync_init_returns_payment_url():
    def handler(request: httpx.Request) -> httpx.Response:
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
    resp = client.init(InitRequest(amount=100, order_id="A-1"))
    assert resp.payment_url == "http://pay"
    client.close()


def test_sync_init_raises_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"Success": False, "ErrorCode": "1051", "Message": "нет средств"},
        )

    client = _client(handler)
    with pytest.raises(InsufficientFundsError):
        client.init(InitRequest(amount=100, order_id="A-1"))
    client.close()
