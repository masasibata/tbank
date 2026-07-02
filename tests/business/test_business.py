from datetime import date, datetime, timezone
from decimal import Decimal

import httpx
import pytest

from tbank.business.aio import BusinessClient as AsyncBusinessClient
from tbank.business.enums import AccountType, TypeOfOperation
from tbank.business.models import BankStatementParams, StatementParams
from tbank.business.sync import BusinessClient as SyncBusinessClient
from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, ServerError
from tbank.core.transport import AsyncTransport, SyncTransport

# Суммы заданы как JSON-числа с дробной частью — проверяем, что дойдут как точный Decimal.
ACCOUNTS_BODY = (
    b'[{"accountNumber":"40802810000000000001","name":"\xd0\x9e\xd1\x81\xd0\xbd\xd0\xbe\xd0\xb2\xd0\xbd\xd0\xbe\xd0\xb9",'
    b'"currency":"643","bankBik":"044525974","accountType":"Current",'
    b'"balance":{"otb":1234.56,"authorized":10.00,"pendingPayments":0,"pendingRequisitions":0}}]'
)


def _async_client(handler):
    transport = AsyncTransport(
        base_url="https://business.tbank.ru/openapi",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        auth=BearerAuth("TKN"),
    )
    return AsyncBusinessClient(token="TKN", transport=transport)


def _sync_client(handler):
    transport = SyncTransport(
        base_url="https://business.tbank.ru/openapi",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        auth=BearerAuth("TKN"),
    )
    return SyncBusinessClient(token="TKN", transport=transport)


async def test_get_accounts_parses_balance_as_exact_decimal():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer TKN"
        assert request.url.path == "/openapi/api/v2/bank-accounts"
        return httpx.Response(
            200, content=ACCOUNTS_BODY, headers={"content-type": "application/json"}
        )

    client = _async_client(handler)
    accounts = await client.get_accounts()
    assert len(accounts) == 1
    acc = accounts[0]
    assert acc.account_type is AccountType.CURRENT
    assert acc.bank_bik == "044525974"
    assert acc.balance is not None
    assert acc.balance.otb == Decimal("1234.56")
    assert isinstance(acc.balance.otb, Decimal)
    await client.aclose()


async def test_get_statement_sends_dates_as_query_and_parses_ops():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "balances": {"balanceBegin": 100, "balanceEnd": 200},
                "operations": [
                    {
                        "operationId": "op-1",
                        "operationDate": "2026-01-15T10:00:00Z",
                        "operationStatus": "Transaction",
                        "typeOfOperation": "Credit",
                        "operationAmount": 50.25,
                        "payPurpose": "оплата",
                        "payer": {"inn": "7700000000", "name": "ООО Ромашка"},
                    }
                ],
                "nextCursor": None,
            },
        )

    client = _async_client(handler)
    params = StatementParams(
        account_number="40802",
        from_=datetime(2026, 1, 1, tzinfo=timezone.utc),
        with_balances=True,
    )
    page = await client.get_statement(params)
    assert seen["path"] == "/openapi/api/v1/statement"
    assert seen["params"]["accountNumber"] == "40802"
    assert seen["params"]["from"].startswith("2026-01-01")
    assert seen["params"]["withBalances"] == "true"
    op = page.operations[0]
    assert op.operation_amount == Decimal("50.25")
    assert op.type_of_operation is TypeOfOperation.CREDIT
    assert op.payer is not None and op.payer.name == "ООО Ромашка"
    await client.aclose()


async def test_iter_statement_follows_cursor_across_pages():
    pages = {
        None: {
            "operations": [
                {"operationId": "op-1", "operationDate": "2026-01-01T00:00:00Z"}
            ],
            "nextCursor": "c1",
        },
        "c1": {
            "operations": [
                {"operationId": "op-2", "operationDate": "2026-01-02T00:00:00Z"}
            ],
            "nextCursor": None,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages[request.url.params.get("cursor")])

    client = _async_client(handler)
    params = StatementParams(
        account_number="40802", from_=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    ids = [op.operation_id async for op in client.iter_statement(params)]
    assert ids == ["op-1", "op-2"]
    await client.aclose()


async def test_forbidden_error_parsed_from_tapi_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "errorId": "60324c74-e4b9-477d-baae-786956876a28",
                "errorMessage": "Неподходящие скопы",
                "errorCode": "FORBIDDEN",
            },
        )

    client = _async_client(handler)
    with pytest.raises(ForbiddenError) as info:
        await client.get_accounts()
    assert info.value.code == "FORBIDDEN"
    assert info.value.http_status == 403
    assert info.value.error_id == "60324c74-e4b9-477d-baae-786956876a28"
    await client.aclose()


async def test_get_bank_statement_parses_saldo_and_period_dates():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["from"] == "2026-01-01"
        assert request.url.params["till"] == "2026-01-31"
        return httpx.Response(
            200,
            json={
                "saldoIn": 1000,
                "income": 500,
                "outcome": 200,
                "saldoOut": 1300,
                "operation": [
                    {
                        "amount": 500,
                        "paymentPurpose": "перевод",
                        "payerInn": "7700000000",
                    }
                ],
            },
        )

    client = _async_client(handler)
    params = BankStatementParams(
        account_number="40802", from_=date(2026, 1, 1), till=date(2026, 1, 31)
    )
    stmt = await client.get_bank_statement(params)
    assert stmt.saldo_out == Decimal("1300")
    assert stmt.operation[0].payer_inn == "7700000000"
    await client.aclose()


def test_sync_get_accounts_and_iter_statement():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/bank-accounts"):
            return httpx.Response(
                200, content=ACCOUNTS_BODY, headers={"content-type": "application/json"}
            )
        return httpx.Response(
            200,
            json={
                "operations": [
                    {"operationId": "s-1", "operationDate": "2026-01-01T00:00:00Z"}
                ],
                "nextCursor": None,
            },
        )

    client = _sync_client(handler)
    accounts = client.get_accounts()
    assert accounts[0].balance is not None
    assert accounts[0].balance.otb == Decimal("1234.56")
    params = StatementParams(
        account_number="40802", from_=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    ids = [op.operation_id for op in client.iter_statement(params)]
    assert ids == ["s-1"]
    client.close()


def test_sync_get_statement_and_bank_statement():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/statement"):
            return httpx.Response(200, json={"operations": [], "nextCursor": None})
        return httpx.Response(200, json={"saldoOut": 42})

    client = _sync_client(handler)
    page = client.get_statement(
        StatementParams(
            account_number="1", from_=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
    )
    assert page.operations == []
    stmt = client.get_bank_statement(BankStatementParams(account_number="1"))
    assert stmt.saldo_out == Decimal("42")
    client.close()


async def test_error_with_non_json_body_falls_back_to_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client = _async_client(handler)
    with pytest.raises(ServerError) as info:
        await client.get_accounts()
    assert info.value.http_status == 500
    assert info.value.code == "500"
    await client.aclose()


def test_public_reexport():
    from tbank.business import BusinessClient, enums, models

    assert BusinessClient.__module__ == "tbank.business.aio"
    assert hasattr(models, "Account")
    assert hasattr(enums, "AccountType")
