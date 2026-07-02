import httpx
from pydantic import Field

from tbank.core.client import BaseAsyncClient, BaseSyncClient
from tbank.core.endpoint import Endpoint
from tbank.core.errors import TBankAPIError
from tbank.core.models import TBankModel
from tbank.core.transport import AsyncTransport, SyncTransport


class _Req(TBankModel):
    order_id: str


class _Resp(TBankModel):
    payment_id: str = Field(default="", alias="PaymentId")


_EP = Endpoint("POST", "/Init", _Resp, _Req)


def _mock_async(handler):
    return AsyncTransport(
        base_url="https://x/v2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


async def test_call_serializes_request_and_parses_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        seen["body"] = _json.loads(request.content)
        return httpx.Response(200, json={"PaymentId": "42"})

    client = BaseAsyncClient(_mock_async(handler))
    resp = await client._call(_EP, _Req(order_id="A-1"))
    assert seen["body"]["OrderId"] == "A-1"
    assert resp.payment_id == "42"
    await client.aclose()


async def test_call_raises_on_http_4xx():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    client = BaseAsyncClient(_mock_async(handler))
    try:
        await client._call(_EP, _Req(order_id="A-1"))
        assert False, "должно бросить"
    except TBankAPIError as err:
        assert err.http_status == 404
    await client.aclose()


def test_sync_call_works():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"PaymentId": "7"})

    transport = SyncTransport(
        base_url="https://x/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    client = BaseSyncClient(transport)
    resp = client._call(_EP, _Req(order_id="A-1"))
    assert resp.payment_id == "7"
    client.close()
