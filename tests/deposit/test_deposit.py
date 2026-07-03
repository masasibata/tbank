import json
from decimal import Decimal

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.deposit.aio import SECURED_URL, DepositClient
from tbank.deposit.enums import (
    AutoProlongationStatus,
    Capitalisation,
    Currency,
    DepositAccountStatus,
    PayFrequency,
)
from tbank.deposit.models import OpenDepositRequest, ReplenishDepositRequest
from tbank.deposit.sync import DepositClient as SyncClient

_DETAILS = {
    "product": "Смарт-депозит",
    "period": 181,
    "balance": {
        "amount": 1000000.55,
        "currencyCode": "RUB",
        "paidAmount": 12000.00,
        "lockedAmount": 0.0,
        "fineAmount": 0.0,
    },
    "agreementInfo": {
        "agreementNumber": "D-1",
        "interestAgreementNumber": "I-1",
        "autoProlongation": {"status": "ACTIVE"},
        "activationDate": "2026-01-01",
        "endingDate": "2026-07-01",
    },
    "accountInfo": {
        "accountNumber": "42301810000000000001",
        "status": "OPENED",
        "rate": 15.5,
        "capitalisation": {"type": "DEPOSIT"},
        "minAmount": 50000.00,
        "maxCurrent": 1000000.55,
        "maxAmount": 5000000.00,
        "withdraw": {"isAccessible": False},
        "replenish": {"isAccessible": True},
        "payFrequency": "MATURITY",
        "openDate": "2026-01-01",
    },
}


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=SECURED_URL, client=client, auth=BearerAuth("T"))


def _client(handler):
    return DepositClient(token="T", transport=_transport(handler))


async def test_get_details():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        assert request.url.path == "/api/v1/deposit/account/details"
        assert request.url.params.get("agreementNumber") == "D-1"
        return httpx.Response(200, json=_DETAILS)

    details = await _client(handler).get_deposit_details("D-1")
    assert details.balance.amount == Decimal("1000000.55")
    assert details.account_info.status == DepositAccountStatus.OPENED
    assert details.account_info.rate == Decimal("15.5")
    assert details.account_info.capitalisation.type == Capitalisation.DEPOSIT
    assert details.account_info.pay_frequency == PayFrequency.MATURITY
    assert details.account_info.withdraw.is_accessible is False
    assert (
        details.agreement_info.auto_prolongation.status == AutoProlongationStatus.ACTIVE
    )


async def test_open_deposit():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/deposit/account/open"
        body = json.loads(request.content)
        assert body["currency"] == "RUB"
        assert body["capitalisation"] == "DEPOSIT"
        assert body["term"] == 181
        return httpx.Response(200, json={"openId": "op-1", "applicationId": "app-1"})

    result = await _client(handler).open_deposit(
        OpenDepositRequest(
            term=181,
            capitalisation=Capitalisation.DEPOSIT,
            currency=Currency.RUB,
            is_replenish_available=True,
            is_withdraw_available=False,
            pay_frequency=PayFrequency.MATURITY,
        )
    )
    assert result.open_id == "op-1"
    assert result.application_id == "app-1"


async def test_replenish_deposit():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/deposit/account/replenish"
        body = json.loads(request.content)
        assert body["amount"] == 25000.5
        assert body["depositAgreement"] == "D-1"
        return httpx.Response(200)

    out = await _client(handler).replenish_deposit(
        ReplenishDepositRequest(
            deposit_agreement="D-1",
            source_agreement="40702810000000000000",
            amount=Decimal("25000.50"),
        )
    )
    assert out is None


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        await client.get_deposit_details("D-1")
    assert exc.value.error_id == "e"


def test_sync_client():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/details"):
            return httpx.Response(200, json=_DETAILS)
        if request.url.path.endswith("/open"):
            return httpx.Response(200, json={"openId": "o", "applicationId": "a"})
        return httpx.Response(500, text="boom")

    client = SyncClient(token="T", transport=_transport(handler, sync=True))
    assert client.get_deposit_details("D-1").product == "Смарт-депозит"
    assert (
        client.open_deposit(
            OpenDepositRequest(
                term=90,
                capitalisation=Capitalisation.ACCOUNT,
                currency=Currency.USD,
                is_replenish_available=False,
                is_withdraw_available=True,
                pay_frequency=PayFrequency.NORMAL,
            )
        ).open_id
        == "o"
    )
    with pytest.raises(TBankAPIError):
        client.replenish_deposit(
            ReplenishDepositRequest(
                deposit_agreement="D-1", source_agreement="S", amount=Decimal("1")
            )
        )
    client.close()
