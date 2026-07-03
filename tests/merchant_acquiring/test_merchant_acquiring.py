import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.merchant_acquiring.aio import PROD_URL, MerchantAcquiringClient
from tbank.merchant_acquiring.enums import OperationType
from tbank.merchant_acquiring.sync import MerchantAcquiringClient as SyncClient


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=PROD_URL, client=client, auth=BearerAuth("T"))


def _client(handler):
    return MerchantAcquiringClient(token="T", transport=_transport(handler))


async def test_list_terminals():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        assert request.url.path == "/openapi/api/v1/tacq/terminals"
        assert request.url.params.get("page") == "2"
        assert request.url.params.get("size") == "10"
        return httpx.Response(
            200,
            json={
                "totalPages": 5,
                "totalElements": 42,
                "first": False,
                "last": False,
                "terminals": [{"id": "t-1", "key": "TERM1"}],
            },
        )

    page = await _client(handler).list_terminals(page=2, size=10)
    assert page.total_elements == 42
    assert page.terminals[0].key == "TERM1"


async def test_list_operations():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openapi/api/v1/tacq/operations/terminal/TERM1"
        assert request.url.params.get("from") == "2026-01-01"
        assert request.url.params.get("till") == "2026-01-31"
        assert request.url.params.get("limit") == "100"
        return httpx.Response(
            200,
            json={
                "lastTransactionDate": "2026-01-31T12:00:00+03:00",
                "operations": [
                    {
                        "rrn": "123456789012",
                        "transactionDate": "2026-01-15T10:30:00+03:00",
                        "amount": 150000,
                        "cardNumber": "220000******0011",
                        "type": "Debit",
                    }
                ],
            },
        )

    ops = await _client(handler).list_operations(
        "TERM1", "2026-01-01", "2026-01-31", limit=100
    )
    assert ops.operations[0].amount == 150000
    assert ops.operations[0].type == OperationType.DEBIT


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        await client.list_terminals()
    assert exc.value.error_id == "e"


def test_sync_client_and_non_json_error():
    def ok(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/terminals"):
            return httpx.Response(
                200,
                json={"totalPages": 1, "totalElements": 0, "first": True, "last": True},
            )
        return httpx.Response(200, json={"operations": []})

    client = SyncClient(token="T", transport=_transport(ok, sync=True))
    assert client.list_terminals().total_elements == 0
    assert client.list_operations("T1", "2026-01-01", "2026-01-31", limit=10).operations == []
    client.close()

    err = SyncClient(
        token="T",
        transport=_transport(lambda r: httpx.Response(500, text="boom"), sync=True),
    )
    with pytest.raises(TBankAPIError) as exc:
        err.list_operations("T1", "2026-01-01", "2026-01-31", limit=10)
    assert exc.value.code == "500"
    err.close()
