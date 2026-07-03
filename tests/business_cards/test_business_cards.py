import json
from decimal import Decimal

import httpx
import pytest

from tbank.business_cards.aio import (
    PROD_URL,
    SANDBOX_URL,
    SECURED_URL,
    BusinessCardsClient,
)
from tbank.business_cards.enums import (
    CardBlockReason,
    CardNetwork,
    CardStatus,
    InputLimitPeriod,
    OutputLimitPeriod,
    ReissueStatus,
)
from tbank.business_cards.models import (
    BatchLimitItem,
    BatchLimitValue,
    BlockCardRequest,
    CreateApplicationRequest,
    SetBatchLimitsRequest,
    SetLimitRequest,
)
from tbank.business_cards.sync import BusinessCardsClient as SyncClient
from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, MutualTLSRequiredError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport


def _transport(handler, base_url, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=base_url, client=client, auth=BearerAuth("T"))


def _client(reg, sec=None):
    return BusinessCardsClient(
        token="T",
        transport=_transport(reg, PROD_URL),
        secured_transport=_transport(sec, SECURED_URL) if sec else None,
    )


def _sync_client(reg, sec=None):
    return SyncClient(
        token="T",
        transport=_transport(reg, PROD_URL, sync=True),
        secured_transport=_transport(sec, SECURED_URL, sync=True) if sec else None,
    )


# --- Карты (обычный хост) ---


async def test_list_and_get_card():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        if request.url.path == "/openapi/api/v1/card":
            assert request.url.params.get("accountNumber") == "40802810000000000001"
            return httpx.Response(
                200,
                json={
                    "offset": 0,
                    "limit": 50,
                    "totalNumber": 1,
                    "cards": [
                        {
                            "ucid": 777,
                            "accountNumber": "40802810000000000001",
                            "cardBin": "220000",
                            "cardLastFourDigits": "0011",
                            "isActive": True,
                            "status": "NORM",
                            "embossedName": "IVAN PETROV",
                        }
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "ucid": 777,
                "accountNumber": "40802810000000000001",
                "cardBin": "220000",
                "cardLastFourDigits": "0011",
                "isActive": True,
                "status": "BLOCKED",
                "embossedName": "IVAN PETROV",
            },
        )

    client = _client(handler)
    page = await client.list_cards(account_number="40802810000000000001")
    assert page.cards[0].ucid == 777
    card = await client.get_card(777)
    assert card.status == CardStatus.BLOCKED


async def test_virtual_card_requisites():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openapi/api/v1/card/virtual/777/requisites"
        return httpx.Response(
            200,
            json={
                "number": "2200000000000011",
                "embossedName": "IVAN PETROV",
                "cvc": "123",
                "expiryDate": {"year": 2030, "month": 5},
            },
        )

    req = await _client(handler).get_virtual_card_requisites(777)
    assert req.cvc == "123"
    assert req.expiry_date.month == 5


async def test_create_and_get_application():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = json.loads(request.content)
            assert body["cardNetwork"] == "MIR"
            return httpx.Response(200, json={"cardIssueApplicationId": "app-1"})
        return httpx.Response(
            200,
            json={
                "cardIssueApplicationId": "app-1",
                "status": "CARD_ISSUED",
                "ucid": 777,
            },
        )

    client = _client(handler)
    created = await client.create_virtual_card_application(
        CreateApplicationRequest(
            employee_identification_application_id="emp-1",
            account_number="40802810000000000001",
            card_network=CardNetwork.MIR,
        )
    )
    assert created.card_issue_application_id == "app-1"
    status = await client.get_virtual_card_application("app-1")
    assert status.ucid == 777


async def test_block_card_and_limits():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/block"):
            assert json.loads(request.content)["reason"] == "LOST"
            return httpx.Response(200, json={})
        if request.url.path.endswith("/cash-limit"):
            assert json.loads(request.content)["limitValue"] == 50000.0
            return httpx.Response(200, json={})
        return httpx.Response(
            200,
            json={
                "ucid": 777,
                "spendLimit": {
                    "limitValue": 100000.00,
                    "limitRemain": 75000.50,
                    "limitPeriod": "MONTH",
                },
                "cashLimit": {
                    "limitValue": 50000.00,
                    "limitRemain": 50000.00,
                    "limitPeriod": "DAY",
                },
            },
        )

    client = _client(handler)
    assert (
        await client.block_card(777, BlockCardRequest(reason=CardBlockReason.LOST))
        is None
    )
    assert (
        await client.set_cash_limit(
            777,
            SetLimitRequest(
                limit_value=Decimal("50000"), limit_period=InputLimitPeriod.DAY
            ),
        )
        is None
    )
    limits = await client.get_card_limits(777)
    assert limits.spend_limit.limit_remain == Decimal("75000.50")
    assert limits.spend_limit.limit_period == OutputLimitPeriod.MONTH


# --- Secured (mTLS) ---


async def test_reissue_secured():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        assert json.loads(request.content)["ucid"] == 777
        return httpx.Response(200, json={"correlationId": "corr-1"})

    def reg(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "READY",
                "info": {
                    "oldUcid": 777,
                    "newUcid": 888,
                    "cardBin": "220000",
                    "cardLastFourDigits": "0022",
                },
            },
        )

    client = _client(reg, sec)
    app = await client.reissue_virtual_card(777)
    assert app.correlation_id == "corr-1"
    result = await client.get_reissue_result("corr-1")
    assert result.status == ReissueStatus.READY
    assert result.info.new_ucid == 888


async def test_spend_limit_and_batch_secured():
    def sec(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/spend-limit"):
            assert json.loads(request.content)["limitPeriod"] == "MONTH"
            return httpx.Response(200, json={})
        body = json.loads(request.content)
        assert body["limits"][0]["ucid"] == 777
        return httpx.Response(
            200,
            json={
                "limits": [
                    {
                        "ucid": 777,
                        "spendLimit": {"isSuccess": True},
                        "cashLimit": {"isSuccess": False, "errorMessage": "denied"},
                    }
                ]
            },
        )

    client = _client(lambda r: httpx.Response(500), sec)
    assert (
        await client.set_spend_limit(
            777,
            SetLimitRequest(
                limit_value=Decimal("100000"), limit_period=InputLimitPeriod.MONTH
            ),
        )
        is None
    )
    result = await client.set_batch_limits(
        SetBatchLimitsRequest(
            limits=[
                BatchLimitItem(
                    ucid=777,
                    spend_limit=BatchLimitValue(
                        limit_period=InputLimitPeriod.DAY, limit_value=100000
                    ),
                )
            ]
        )
    )
    assert result.limits[0].spend_limit.is_success is True
    assert result.limits[0].cash_limit.error_message == "denied"


async def test_v3_lists_secured():
    def sec(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/virtual/issue/application"):
            return httpx.Response(
                200,
                json=[
                    {
                        "cardIssueApplicationId": "app-1",
                        "status": "CARD_ISSUED",
                        "ucid": "777",
                    }
                ],
            )
        assert request.url.path == "/api/v3/company/card"
        return httpx.Response(
            200,
            json={
                "offset": 0,
                "limit": 50,
                "cards": [
                    {
                        "ucid": 777,
                        "accountNumber": "40802810000000000001",
                        "cardBin": "220000",
                        "cardLastFourDigits": "0011",
                        "embossedName": "IVAN PETROV",
                        "isActive": True,
                        "isVirtual": True,
                        "status": "NORM",
                    }
                ],
            },
        )

    client = _client(lambda r: httpx.Response(500), sec)
    apps = await client.list_virtual_card_applications(limit=10, offset=0)
    assert apps[0].ucid == "777"
    cards = await client.list_company_cards()
    assert cards.cards[0].is_virtual is True


async def test_secured_without_cert_raises():
    client = _client(lambda r: httpx.Response(200, json={}))
    with pytest.raises(MutualTLSRequiredError):
        await client.reissue_virtual_card(777)
    with pytest.raises(MutualTLSRequiredError):
        await client.list_company_cards()


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        await client.list_cards()
    assert exc.value.error_id == "e"


# --- Синхронный клиент ---


def test_sync_client():
    def reg(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/block"):
            return httpx.Response(200, json={})
        return httpx.Response(
            200, json={"offset": 0, "limit": 50, "totalNumber": 0, "cards": []}
        )

    def sec(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"correlationId": "c"})

    client = _sync_client(reg, sec)
    assert client.list_cards().total_number == 0
    assert client.block_card(1, BlockCardRequest(reason=CardBlockReason.FRAUD)) is None
    assert client.reissue_virtual_card(5).correlation_id == "c"
    client.close()

    err = _sync_client(lambda r: httpx.Response(500, text="boom"))
    with pytest.raises(TBankAPIError):
        err.get_card(1)
    err.close()


def _surface_handler(request: httpx.Request) -> httpx.Response:
    p, m = request.url.path.replace("/openapi", ""), request.method
    card = {
        "ucid": 1,
        "accountNumber": "40802810000000000001",
        "cardBin": "220000",
        "cardLastFourDigits": "0011",
        "isActive": True,
        "status": "NORM",
        "embossedName": "IVAN",
    }
    if p == "/api/v1/card":
        body = {"offset": 0, "limit": 50, "totalNumber": 1, "cards": [card]}
    elif p.endswith("/requisites"):
        body = {
            "number": "2200000000000011",
            "embossedName": "IVAN",
            "cvc": "123",
            "expiryDate": {"year": 2030, "month": 5},
        }
    elif p == "/api/v1/card/virtual/issue/application" and m == "POST":
        body = {"cardIssueApplicationId": "app"}
    elif p.startswith("/api/v1/card/virtual/issue/application/"):
        body = {"cardIssueApplicationId": "app", "status": "NEW"}
    elif p == "/api/v3/card/virtual/issue/application":
        return httpx.Response(
            200, json=[{"cardIssueApplicationId": "app", "status": "NEW"}]
        )
    elif p == "/api/v3/company/card":
        body = {"offset": 0, "limit": 50, "cards": []}
    elif (
        p.endswith("/block") or p.endswith("/cash-limit") or p.endswith("/spend-limit")
    ):
        body = {}
    elif p.endswith("/limits") and m == "GET":
        body = {
            "ucid": 1,
            "spendLimit": {
                "limitValue": 100,
                "limitRemain": 50,
                "limitPeriod": "MONTH",
            },
            "cashLimit": {"limitValue": 100, "limitRemain": 100, "limitPeriod": "DAY"},
        }
    elif p == "/api/v3/card/limits/set_batch":
        body = {"limits": [{"ucid": 1, "spendLimit": {"isSuccess": True}}]}
    elif p == "/api/v1/card/virtual/reissue":
        body = {"correlationId": "corr"}
    elif p.endswith("/reissue/result"):
        body = {"status": "IN_PROGRESS"}
    elif p.startswith("/api/v1/card/"):
        body = card
    else:  # pragma: no cover
        raise AssertionError(f"unrouted {m} {p}")
    return httpx.Response(200, json=body)


def test_sync_full_surface():
    client = _sync_client(_surface_handler, _surface_handler)
    limit = SetLimitRequest(
        limit_value=Decimal("100"), limit_period=InputLimitPeriod.DAY
    )
    assert client.list_cards().total_number == 1
    assert client.get_card(1).ucid == 1
    assert client.get_virtual_card_requisites(1).cvc == "123"
    assert client.block_card(1, BlockCardRequest(reason=CardBlockReason.LOST)) is None
    assert client.list_company_cards().cards == []
    assert (
        client.create_virtual_card_application(
            CreateApplicationRequest(
                employee_identification_application_id="e",
                account_number="40802810000000000001",
                card_network=CardNetwork.MIR,
            )
        ).card_issue_application_id
        == "app"
    )
    assert client.get_virtual_card_application("app").card_issue_application_id == "app"
    assert (
        client.list_virtual_card_applications(limit=10, offset=0)[0].status.value
        == "NEW"
    )
    assert client.reissue_virtual_card(1).correlation_id == "corr"
    assert client.get_reissue_result("corr").status == ReissueStatus.IN_PROGRESS
    assert client.get_card_limits(1).spend_limit.limit_value == Decimal("100")
    assert client.set_cash_limit(1, limit) is None
    assert client.set_spend_limit(1, limit) is None
    assert (
        client.set_batch_limits(
            SetBatchLimitsRequest(
                limits=[
                    BatchLimitItem(
                        ucid=1,
                        spend_limit=BatchLimitValue(
                            limit_period=InputLimitPeriod.DAY, limit_value=100
                        ),
                    )
                ]
            )
        )
        .limits[0]
        .spend_limit.is_success
        is True
    )
    client.close()


def test_url_constants():
    assert SANDBOX_URL.endswith("/sandbox")
    assert PROD_URL == "https://business.tbank.ru/openapi"
