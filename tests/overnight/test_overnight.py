import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.overnight.aio import SECURED_URL, OvernightClient
from tbank.overnight.enums import AutoPayType
from tbank.overnight.sync import OvernightClient as SyncClient

_INFO = {
    "agreementNumber": "OV-1",
    "amount": "150000.00",
    "blockedAmount": "0.00",
    "percentRate": "12.5",
    "isAccessible": True,
    "isDealActive": True,
    "autoPay": {"isAccessible": True, "isActive": True, "type": "RestCurrent"},
    "actualDeal": {
        "opened": "2026-07-01T21:00:00+03:00",
        "closed": "2026-07-02T09:00:00+03:00",
        "percentRate": "12.5",
        "amount": "150000.00",
        "paidAmount": "150051.37",
    },
    "settings": {
        "minAmount": "1000.00",
        "maxAmount": "10000000.00",
        "currentAmount": "5000.00",
    },
}


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=SECURED_URL, client=client, auth=BearerAuth("T"))


def _client(handler):
    return OvernightClient(token="T", transport=_transport(handler))


async def test_get_overnight_info():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.host == "secured-openapi.tbank.ru"
        assert request.url.path == "/api/v1/overnight/info"
        assert request.url.params.get("agreementNumber") == "OV-1"
        return httpx.Response(200, json=_INFO)

    info = await _client(handler).get_overnight_info("OV-1")
    assert info.amount == "150000.00"
    assert info.auto_pay.type == AutoPayType.REST_CURRENT
    assert info.actual_deal.paid_amount == "150051.37"
    assert info.settings.max_amount == "10000000.00"


async def test_replenish_overnight():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/overnight/replenish"
        assert request.url.params.get("agreementNumber") == "OV-1"
        assert request.url.params.get("amount") == "50000.00"
        return httpx.Response(200)

    assert await _client(handler).replenish_overnight("OV-1", "50000.00") is None


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        await client.get_overnight_info("OV-1")
    assert exc.value.error_id == "e"


def test_sync_client():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/info"):
            return httpx.Response(200, json=_INFO)
        return httpx.Response(500, text="boom")

    client = SyncClient(token="T", transport=_transport(handler, sync=True))
    assert client.get_overnight_info("OV-1").agreement_number == "OV-1"
    with pytest.raises(TBankAPIError):
        client.replenish_overnight("OV-1", "1.00")
    client.close()
