from decimal import Decimal

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.special_accounts.aio import PROD_URL, SpecialAccountsClient
from tbank.special_accounts.enums import EtpArrestStatus
from tbank.special_accounts.sync import SpecialAccountsClient as SyncClient

_OPS = {
    "arrests": {
        "sum": 12000.50,
        "values": [
            {
                "id": "ar-1",
                "amount": 12000.50,
                "currency": "RUB",
                "status": "ACTIVE",
                "date": "2026-06-01T10:00:00+03:00",
                "unblockDate": "2026-09-01T10:00:00+03:00",
                "circumstances": "исполнительное производство",
            }
        ],
    },
    "etpFees": [
        {
            "id": "etp-1",
            "amount": 500.00,
            "currency": "RUB",
            "status": "PAYED",
            "date": "2026-05-01T10:00:00+03:00",
            "payedAmount": 500.00,
            "senderInn": "1234567890",
            "recipient": {"inn": "0987654321", "name": "ЭТП"},
            "bank": {"bik": "044525225", "name": "Т-Банк"},
        }
    ],
}


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=PROD_URL, client=client, auth=BearerAuth("T"))


def _client(handler):
    return SpecialAccountsClient(token="T", transport=_transport(handler))


async def test_get_arrest_etp_operations():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        assert request.url.path == "/openapi/api/v1/special-accounts/arrest-etp"
        assert request.url.params.get("accountNumber") == "40817810000000000001"
        assert request.url.params.get("from") == "2026-01-01"
        assert request.url.params.get("till") == "2026-06-30"
        return httpx.Response(200, json=_OPS)

    ops = await _client(handler).get_arrest_etp_operations(
        "40817810000000000001", "2026-01-01", "2026-06-30"
    )
    assert ops.arrests.sum == Decimal("12000.50")
    assert ops.arrests.values[0].status == EtpArrestStatus.ACTIVE
    assert ops.etp_fees[0].amount == Decimal("500.00")
    assert ops.etp_fees[0].recipient.inn == "0987654321"
    assert ops.etp_fees[0].bank.bik == "044525225"


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError):
        await client.get_arrest_etp_operations("acc", "2026-01-01", "2026-01-31")


def test_sync_client_success():
    client = SyncClient(
        token="T",
        transport=_transport(lambda r: httpx.Response(200, json=_OPS), sync=True),
    )
    ops = client.get_arrest_etp_operations("acc", "2026-01-01", "2026-01-31")
    assert ops.arrests.sum == Decimal("12000.50")
    client.close()


def test_sync_non_json_error():
    client = SyncClient(
        token="T",
        transport=_transport(lambda r: httpx.Response(500, text="boom"), sync=True),
    )
    with pytest.raises(TBankAPIError) as exc:
        client.get_arrest_etp_operations("acc", "2026-01-01", "2026-01-31")
    assert exc.value.code == "500"
    client.close()
