import json
from decimal import Decimal

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError, ValidationError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.direct_debit.aio import SECURED_URL, DirectDebitClient
from tbank.direct_debit.enums import (
    AgreementStatus,
    PaymentRequestStatus,
    RuleType,
)
from tbank.direct_debit.models import (
    CreatePaymentRequest,
    PaymentRequisites,
    RecurrentRuleCreate,
    RecurrentRuleDetails,
    RecurrentRuleUpdate,
    ReplenishmentFilter,
    TriggerAmount,
    TriggerRuleCreate,
    TriggerRuleDetails,
)
from tbank.direct_debit.sync import DirectDebitClient as SyncClient


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=SECURED_URL, client=client, auth=BearerAuth("T"))


def _client(handler):
    return DirectDebitClient(token="T", transport=_transport(handler))


def _sync_client(handler):
    return SyncClient(token="T", transport=_transport(handler, sync=True))


def _requisites():
    return PaymentRequisites(
        payer_account="4" * 20,
        payer_name="ООО Ромашка",
        payer_inn="1234567890",
        payer_kpp="0",
        payer_bic="044525225",
        payer_cor_account="3" * 20,
        recipient_account="4" * 20,
        purpose="Оплата по договору",
        amount=Decimal("1000.50"),
    )


# --- Правила ---


async def test_create_recurrent_rule_body_and_idempotency():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        assert request.url.path == "/api/v1/rules"
        assert request.headers.get("Idempotency-Key")
        body = json.loads(request.content)
        assert body["type"] == "Recurrent"
        assert body["requisites"]["payerBIC"] == "044525225"
        assert body["requisites"]["payerINN"] == "1234567890"
        assert body["requisites"]["amount"] == 1000.5
        return httpx.Response(200, json={"ruleId": "rule-1"})

    client = _client(handler)
    res = await client.create_rule(
        RecurrentRuleCreate(
            agreement_id="agr-1", cron_expr="0 12 * * *", requisites=_requisites()
        )
    )
    assert res.rule_id == "rule-1"


async def test_create_trigger_rule():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["type"] == "Trigger"
        assert body["amount"]["percent"] == 0.5
        assert body["replenishmentFilter"]["category"] == "CounterpartyIncome"
        return httpx.Response(200, json={"ruleId": "rule-2"})

    client = _client(handler)
    res = await client.create_rule(
        TriggerRuleCreate(
            agreement_id="agr-1",
            amount=TriggerAmount(percent=Decimal("0.5")),
            replenishment_filter=ReplenishmentFilter(category="CounterpartyIncome"),
            requisites=_requisites(),
        ),
        idempotency_key="k-1",
    )
    assert res.rule_id == "rule-2"


async def test_get_and_update_rule_union():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PUT":
            assert json.loads(request.content)["type"] == "Recurrent"
            return httpx.Response(
                200,
                json={
                    "type": "Trigger",
                    "id": "rule-3",
                    "agreementId": "agr-1",
                    "amount": {"fixed": 250.0},
                    "replenishmentFilter": {"category": "CashIn"},
                    "requisites": {
                        "payerAccount": "4" * 20,
                        "payerName": "N",
                        "payerINN": "1234567890",
                        "payerKPP": "0",
                        "payerBIC": "044525225",
                        "payerCorAccount": "3" * 20,
                        "recipientAccount": "4" * 20,
                        "purpose": "p",
                    },
                },
            )
        return httpx.Response(
            200,
            json={
                "type": "Recurrent",
                "id": "rule-3",
                "agreementId": "agr-1",
                "cronExpr": "0 12 * * *",
                "requisites": {
                    "payerAccount": "4" * 20,
                    "payerName": "N",
                    "payerINN": "1234567890",
                    "payerKPP": "0",
                    "payerBIC": "044525225",
                    "payerCorAccount": "3" * 20,
                    "recipientAccount": "4" * 20,
                    "purpose": "p",
                    "amount": 1000.5,
                },
            },
        )

    client = _client(handler)
    got = await client.get_rule("rule-3")
    assert isinstance(got, RecurrentRuleDetails)
    assert got.requisites.amount == Decimal("1000.5")
    upd = await client.update_rule(
        "rule-3", RecurrentRuleUpdate(cron_expr="0 12 * * *", requisites=_requisites())
    )
    assert isinstance(upd, TriggerRuleDetails)
    assert upd.amount.fixed == Decimal("250.0")


async def test_list_rules_v1_and_v2():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/rules":
            assert request.url.params.get("agreementId") == "agr-1"
            return httpx.Response(
                200,
                json={
                    "offset": 0,
                    "limit": 10,
                    "size": 1,
                    "total": 1,
                    "results": [
                        {
                            "type": "Recurrent",
                            "id": "rule-1",
                            "amount": 500.0,
                            "cronExpr": "0 12 * * *",
                        }
                    ],
                },
            )
        assert request.url.path == "/api/v2/rules"
        assert b"ruleTypes=Trigger" in request.url.query
        return httpx.Response(
            200,
            json={"offset": 0, "limit": 10, "size": 0, "total": 0, "results": []},
        )

    client = _client(handler)
    v1 = await client.list_rules("agr-1")
    assert v1.results[0].type == RuleType.RECURRENT
    v2 = await client.list_rules_v2(rule_types=[RuleType.TRIGGER])
    assert v2.total == 0


async def test_delete_rule_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        return httpx.Response(200, json={})

    client = _client(handler)
    assert await client.delete_rule("rule-1") is None


# --- Платёжные требования ---


async def test_create_payment_request_and_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/requests"
        assert request.headers.get("Idempotency-Key")
        body = json.loads(request.content)
        assert body["amount"] == 1000.5
        assert body["docType"] == "PaymentRequest"
        return httpx.Response(200, json={"id": "req-1"})

    client = _client(handler)
    res = await client.create_payment_request(
        CreatePaymentRequest(
            payer_account="4" * 20,
            payer_name="N",
            payer_inn="1234567890",
            payer_kpp="0",
            payer_bic="044525225",
            payer_cor_account="3" * 20,
            recipient_account="4" * 20,
            purpose="p",
            amount=Decimal("1000.50"),
        )
    )
    assert res.id == "req-1"


async def test_list_and_get_payment_request():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/requests":
            assert request.url.params.get("startDate") == "2026-01-01"
            return httpx.Response(
                200,
                json={
                    "offset": 0,
                    "limit": 10,
                    "size": 1,
                    "total": 1,
                    "results": [
                        {
                            "id": "req-1",
                            "creationDate": "2026-01-05",
                            "docType": "PaymentRequest",
                            "direction": "Debit",
                            "status": "Pending",
                        }
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "req-1",
                "creationDate": "2026-01-05",
                "docType": "PaymentRequest",
                "amount": 1000.50,
                "payerAccount": "4" * 20,
                "payerName": "N",
                "payerINN": "1234567890",
                "recipientAccount": "4" * 20,
                "purpose": "p",
                "direction": "Debit",
                "status": "Completed",
            },
        )

    client = _client(handler)
    page = await client.list_payment_requests(start_date="2026-01-01")
    assert page.results[0].status == PaymentRequestStatus.PENDING
    details = await client.get_payment_request("req-1")
    assert details.amount == Decimal("1000.50")
    assert details.status == PaymentRequestStatus.COMPLETED


async def test_revoke_and_file():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/revoke"):
            assert request.headers.get("Idempotency-Key")
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"content": "JVBERi0="})

    client = _client(handler)
    assert await client.revoke_payment_request("req-1") is None
    pdf = await client.get_payment_request_file("req-1")
    assert pdf.content == "JVBERi0="


# --- Соглашения ---


async def test_agreements_list_get_file_url():
    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if p == "/api/v1/agreements":
            return httpx.Response(
                200,
                json={
                    "offset": 0,
                    "limit": 10,
                    "size": 1,
                    "total": 1,
                    "results": [{"id": "agr-1", "type": "Payer", "status": "Active"}],
                },
            )
        if p.endswith("/file"):
            return httpx.Response(200, json={"filename": "a.pdf", "content": "JVBE"})
        if p.endswith("/url"):
            return httpx.Response(200, json={"url": "https://sign"})
        return httpx.Response(
            200,
            json={
                "id": "agr-1",
                "number": "A-100",
                "recipientRequisites": {"name": "Получатель", "inn": "1234567890"},
                "payerRequisites": {"name": "Плательщик"},
                "startDate": "2026-01-01T00:00:00",
                "maxSum": 1000000.00,
                "status": "Active",
            },
        )

    client = _client(handler)
    page = await client.list_agreements()
    assert page.results[0].status == AgreementStatus.ACTIVE
    details = await client.get_agreement("agr-1")
    assert details.recipient_requisites.inn == "1234567890"
    assert details.max_sum == Decimal("1000000.00")
    f = await client.get_agreement_file("agr-1")
    assert f.filename == "a.pdf"
    url = await client.get_agreement_url()
    assert url.url == "https://sign"


# --- Ошибки ---


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e1", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        await client.list_agreements()
    assert exc.value.error_id == "e1"

    client = _client(
        lambda r: httpx.Response(
            400, json={"errorId": "e2", "errorMessage": "bad", "errorCode": "V1"}
        )
    )
    with pytest.raises(ValidationError):
        await client.get_agreement("x")


async def test_error_non_json():
    client = _client(lambda r: httpx.Response(500, text="boom"))
    with pytest.raises(TBankAPIError) as exc:
        await client.list_agreements()
    assert exc.value.code == "500"


# --- Синхронный клиент (полная поверхность) ---


def _surface_handler(request: httpx.Request) -> httpx.Response:
    p, m = request.url.path, request.method
    rule_details = {
        "type": "Recurrent",
        "id": "r",
        "agreementId": "a",
        "cronExpr": "0 12 * * *",
        "requisites": {
            "payerAccount": "4" * 20,
            "payerName": "N",
            "payerINN": "1234567890",
            "payerKPP": "0",
            "payerBIC": "044525225",
            "payerCorAccount": "3" * 20,
            "recipientAccount": "4" * 20,
            "purpose": "p",
            "amount": 1,
        },
    }
    req_details = {
        "id": "req",
        "creationDate": "2026-01-01",
        "docType": "PaymentRequest",
        "amount": 1,
        "payerAccount": "4" * 20,
        "payerName": "N",
        "payerINN": "1234567890",
        "recipientAccount": "4" * 20,
        "purpose": "p",
        "direction": "Debit",
        "status": "Pending",
    }

    def paged(item):
        return {"offset": 0, "limit": 10, "size": 1, "total": 1, "results": [item]}

    if m == "DELETE":
        body = {}
    elif p.endswith("/revoke"):
        body = {}
    elif p == "/api/v1/rules":
        body = (
            {"ruleId": "r"}
            if m == "POST"
            else paged(
                {"type": "Recurrent", "id": "r", "amount": 1, "cronExpr": "0 12 * * *"}
            )
        )
    elif p == "/api/v2/rules":
        body = paged(rule_details)
    elif p.startswith("/api/v1/rules/"):
        body = rule_details
    elif p == "/api/v1/requests":
        body = (
            {"id": "req"}
            if m == "POST"
            else paged(
                {
                    "id": "req",
                    "creationDate": "2026-01-01",
                    "docType": "PaymentRequest",
                    "direction": "Debit",
                    "status": "Pending",
                }
            )
        )
    elif p.endswith("/file") and "/requests/" in p:
        body = {"content": "JVBE"}
    elif p.startswith("/api/v1/requests/"):
        body = req_details
    elif p == "/api/v1/agreements":
        body = paged({"id": "a", "type": "Payer", "status": "Active"})
    elif p.endswith("/url"):
        body = {"url": "https://sign"}
    elif p.endswith("/file"):
        body = {"filename": "a.pdf", "content": "JVBE"}
    elif p.startswith("/api/v1/agreements/"):
        body = {
            "id": "a",
            "number": "A-1",
            "recipientRequisites": {"name": "R"},
            "payerRequisites": {"name": "P"},
            "startDate": "2026-01-01T00:00:00",
        }
    else:  # pragma: no cover
        raise AssertionError(f"unrouted {m} {p}")
    return httpx.Response(200, json=body)


def test_sync_full_surface():
    client = _sync_client(_surface_handler)
    req = _requisites()
    assert (
        client.create_rule(
            RecurrentRuleCreate(
                agreement_id="a", cron_expr="0 12 * * *", requisites=req
            )
        ).rule_id
        == "r"
    )
    assert client.list_rules("a").total == 1
    assert client.list_rules_v2(rule_types=[RuleType.RECURRENT]).total == 1
    assert isinstance(client.get_rule("r"), RecurrentRuleDetails)
    client.update_rule("r", RecurrentRuleUpdate(cron_expr="0 12 * * *", requisites=req))
    assert client.delete_rule("r") is None

    pr = CreatePaymentRequest(
        payer_account="4" * 20,
        payer_name="N",
        payer_inn="1234567890",
        payer_kpp="0",
        payer_bic="044525225",
        payer_cor_account="3" * 20,
        recipient_account="4" * 20,
        purpose="p",
        amount=Decimal("1"),
    )
    assert client.create_payment_request(pr).id == "req"
    assert client.list_payment_requests().total == 1
    assert client.get_payment_request("req").id == "req"
    assert client.revoke_payment_request("req") is None
    assert client.get_payment_request_file("req").content == "JVBE"

    assert client.list_agreements().total == 1
    assert client.get_agreement("a").number == "A-1"
    assert client.get_agreement_file("a").filename == "a.pdf"
    assert client.get_agreement_url().url == "https://sign"
    client.close()


def test_sync_error_mapping():
    client = _sync_client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError):
        client.list_agreements()
    client.close()


def test_sandbox_url_constant():
    from tbank.direct_debit.aio import SANDBOX_SECURED_URL

    assert SANDBOX_SECURED_URL.endswith("/sandbox/secured")
