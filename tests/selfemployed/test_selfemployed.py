import json
import uuid
from datetime import date, datetime
from decimal import Decimal

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, MutualTLSRequiredError, ValidationError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.selfemployed.aio import (
    PROD_URL,
    SANDBOX_SECURED_URL,
    SECURED_URL,
    SelfEmployedClient,
)
from tbank.selfemployed.enums import (
    AddressKind,
    DocumentType,
    DraftStatus,
    PaymentInfoStatus,
    PayResultStatus,
    PhoneType,
    ReceiptsRequestStatus,
    ReceiptStatus,
    RecipientStatus,
    RevenueTypeCode,
    SelfEmployedStatus,
    SubmitResultStatus,
)
from tbank.selfemployed.models import (
    AddRecipientsByRequisitesRequest,
    CreatePaymentRegistryRequest,
    CreateRecipientsRequest,
    DateRange,
    ListRecipientsRequest,
    ListRegistriesRequest,
    RecipientAddress,
    RecipientBankInfo,
    RecipientByRequisites,
    RecipientDocument,
    RecipientDraft,
    RecipientPhone,
    RegistrationInfo,
    RegistryPayment,
    SelfEmployedInfo,
)
from tbank.selfemployed.sync import SelfEmployedClient as SyncSelfEmployedClient


def _reg_transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=PROD_URL, client=client, auth=BearerAuth("T"))


def _sec_transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=SECURED_URL, client=client, auth=BearerAuth("T"))


def _client(reg_handler, sec_handler=None):
    return SelfEmployedClient(
        token="T",
        transport=_reg_transport(reg_handler),
        secured_transport=_sec_transport(sec_handler) if sec_handler else None,
    )


# --- Самозанятые (обычный хост) ---


async def test_create_recipients_full_draft_and_correlation_echo():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        assert request.url.path == "/openapi/api/v1/self-employed/recipients/create"
        assert request.headers["Authorization"] == "Bearer T"
        body = json.loads(request.content)
        seen["body"] = body
        return httpx.Response(200, json={"correlationId": body["correlationId"]})

    client = _client(handler)
    draft = RecipientDraft(
        number=1,
        first_name="Иван",
        last_name="Петров",
        birth_date=date(1990, 1, 2),
        birth_place="Москва",
        citizenship="РФ",
        phones=[RecipientPhone(type=PhoneType.MOBILE, number="+79990000000")],
        addresses=[
            RecipientAddress(
                type=AddressKind.REGISTRATION,
                postal_code="101000",
                state="Москва",
                city="Москва",
            )
        ],
        documents=[
            RecipientDocument(
                type=DocumentType.PASSPORT,
                serial="4500",
                issued_on=date(2010, 3, 4),
                organization="ОВД",
            )
        ],
        registration_info=RegistrationInfo(oktmo="45000000", activity_codes=["62.01"]),
    )
    cid = await client.create_recipients(
        CreateRecipientsRequest(recipients=[draft], correlation_id="cid-1")
    )
    assert cid == "cid-1"
    b = seen["body"]
    assert b["recipients"][0]["phones"][0]["type"] == "Мобильный"
    assert b["recipients"][0]["documents"][0]["date"] == "2010-03-04"  # alias issued_on
    assert b["recipients"][0]["birthPlace"] == "Москва"
    await client.aclose()


async def test_create_recipients_autogenerates_correlation_id():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"correlationId": "x"})

    client = _client(handler)
    cid = await client.create_recipients(
        CreateRecipientsRequest(
            recipients=[
                RecipientDraft(
                    number=1,
                    first_name="И",
                    last_name="П",
                    birth_date=date(1990, 1, 2),
                    birth_place="М",
                    citizenship="РФ",
                )
            ]
        )
    )
    uuid.UUID(cid)  # валиден как uuid — сгенерирован SDK
    await client.aclose()


async def test_create_recipients_result_parses_statuses():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("correlationId") == "cid-1"
        return httpx.Response(
            200,
            json={
                "recipientResults": [
                    {
                        "number": 1,
                        "firstName": "И",
                        "lastName": "П",
                        "recipientId": 55,
                        "status": "CREATED",
                    },
                    {
                        "number": 2,
                        "firstName": "А",
                        "lastName": "С",
                        "status": "ERROR",
                        "errors": [
                            {"fieldName": "inn", "errorDescription": "плохой ИНН"}
                        ],
                    },
                ]
            },
        )

    client = _client(handler)
    res = await client.get_create_recipients_result("cid-1")
    assert res.recipient_results[0].recipient_id == 55
    assert res.recipient_results[0].status is DraftStatus.CREATED
    assert res.recipient_results[1].errors[0].field_name == "inn"
    await client.aclose()


async def test_add_recipients_by_requisites_and_result():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = json.loads(request.content)
            assert body["recipients"][0]["bankInfo"]["accountNumber"] == "40817"
            return httpx.Response(200, json={"correlationId": body["correlationId"]})
        return httpx.Response(
            200,
            json={
                "recipientResults": [
                    {"number": 1, "firstName": "И", "lastName": "П", "status": "QUEUED"}
                ]
            },
        )

    client = _client(handler)
    cid = await client.add_recipients_by_requisites(
        AddRecipientsByRequisitesRequest(
            correlation_id="cid-2",
            recipients=[
                RecipientByRequisites(
                    number=1,
                    first_name="И",
                    last_name="П",
                    bank_info=RecipientBankInfo(
                        account_number="40817", bank_bic="044525974"
                    ),
                )
            ],
        )
    )
    assert cid == "cid-2"
    res = await client.get_add_recipients_result("cid-2")
    assert res.recipient_results[0].status is DraftStatus.QUEUED
    await client.aclose()


async def test_list_recipients_sends_date_range_and_parses_info():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "recipients": [
                    {
                        "id": 55,
                        "status": "ACTIVE",
                        "selfEmployedStatus": "ACTIVE",
                        "selfEmployedIdentificationStatus": "IDENTIFIED",
                        "selfEmployedAgreementStatus": "AGREED",
                        "firstName": "Иван",
                        "lastName": "Петров",
                        "bankInfo": {"accountNumber": "40817", "bankBic": "044525974"},
                        "phones": [{"type": "Рабочий", "number": "+7"}],
                        "inn": "770012345678",
                    }
                ]
            },
        )

    client = _client(handler)
    res = await client.list_recipients(
        ListRecipientsRequest(
            recipient_ids=[55],
            creation_date=DateRange(
                from_=datetime(2026, 1, 1), to=datetime(2026, 12, 31)
            ),
            limit=10,
        )
    )
    assert "from" in seen["body"]["creationDate"]
    assert seen["body"]["creationDate"]["to"].startswith("2026-12-31")
    r = res.recipients[0]
    assert r.status is RecipientStatus.ACTIVE
    assert r.self_employed_status is SelfEmployedStatus.ACTIVE
    assert r.phones is not None and r.phones[0].type is PhoneType.WORK
    await client.aclose()


# --- Платёжный реестр: создание (обычный хост) ---


async def test_create_registry_sends_sum_as_number_on_regular_host():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"correlationId": seen["body"]["correlationId"]}
        )

    client = _client(handler)
    cid = await client.create_payment_registry(
        CreatePaymentRegistryRequest(
            correlation_id="cid-3",
            payments=[
                RegistryPayment(
                    number=1,
                    account_number="40820",
                    payment_purpose="Оплата услуг",
                    self_employed_info=SelfEmployedInfo(
                        first_name="Иван", last_name="Петров"
                    ),
                    sum=Decimal("1500.50"),
                    revenue_type_code=RevenueTypeCode.CODE_1,
                )
            ],
        )
    )
    assert cid == "cid-3"
    pay = seen["body"]["payments"][0]
    assert pay["sum"] == 1500.5 and isinstance(pay["sum"], (int, float))
    assert pay["revenueTypeCode"] == "1"
    await client.aclose()


async def test_create_registry_result():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "paymentRegistryId": 987,
                "status": "CREATED",
                "paymentErrors": [
                    {
                        "number": 2,
                        "accountNumber": "40820",
                        "errors": [{"fieldName": "sum", "errorDescription": "мало"}],
                    }
                ],
            },
        )

    client = _client(handler)
    res = await client.get_create_registry_result("cid-3")
    assert res.payment_registry_id == 987
    assert res.status is DraftStatus.CREATED
    assert res.payment_errors[0].errors[0].field_name == "sum"
    await client.aclose()


# --- Платёжный реестр: secured (mTLS) ---


def _sec_dispatch(paths):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        return paths(request)

    return handler


async def test_submit_pay_receipts_route_to_secured_host():
    calls = []

    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        path = request.url.path
        calls.append(path)
        if path.endswith("/submit"):
            body = json.loads(request.content)
            assert body == {"paymentRegistryId": 987, "correlationId": "cid-4"}
            return httpx.Response(200, json={"correlationId": "cid-4"})
        if path.endswith("/pay"):
            return httpx.Response(
                200,
                json={"correlationId": json.loads(request.content)["correlationId"]},
            )
        if path.endswith("/receipts"):
            return httpx.Response(
                200,
                json={"correlationId": json.loads(request.content)["correlationId"]},
            )
        raise AssertionError(path)

    def reg(request: httpx.Request) -> httpx.Response:
        raise AssertionError("secured method must not hit regular host")

    client = _client(reg, sec)
    assert await client.submit_payment_registry(987, correlation_id="cid-4") == "cid-4"
    pay_cid = await client.pay_payment_registry(987)
    uuid.UUID(pay_cid)  # авто-generated
    rec_cid = await client.request_receipts(987, correlation_id="cid-6")
    assert rec_cid == "cid-6"
    assert any(p.endswith("/submit") for p in calls)
    await client.aclose()


async def test_submit_pay_receipts_results_parse_secured():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        path = request.url.path
        if path.endswith("/submit/result"):
            assert request.url.params.get("correlationId") == "c"
            return httpx.Response(
                200,
                json={
                    "paymentRegistryId": 987,
                    "status": "ERROR",
                    "error": {"errorCode": "E1", "errorMessage": "нет денег"},
                },
            )
        if path.endswith("/pay/result"):
            assert json.loads(request.content) == {"correlationId": "c"}
            return httpx.Response(
                200,
                json={
                    "paymentRegistryId": 987,
                    "status": "PART_EXEC",
                    "count": 2,
                    "error": {"errorCode": "E2", "errorDescription": "частично"},
                    "paymentResults": [
                        {"number": 1, "paymentStatus": "EXECUTED"},
                        {
                            "number": 2,
                            "paymentStatus": "ERROR",
                            "errors": [{"fieldName": "acc", "errorDescription": "bad"}],
                        },
                    ],
                },
            )
        # v2 receipts/result
        assert path == "/api/v2/self-employed/payment-registry/receipts/result"
        return httpx.Response(
            200,
            content=(
                b'{"status":"FINISHED","receipts":[{"number":1,'
                b'"selfEmployedInfo":{"firstName":"\xd0\x98","lastName":"\xd0\x9f","inn":"770012345678"},'
                b'"link":"https://r/1","sum":1500.50,"status":"SUCCESS"}]}'
            ),
            headers={"content-type": "application/json"},
        )

    client = _client(lambda r: httpx.Response(500), sec)
    submit = await client.get_submit_result("c")
    assert submit.status is SubmitResultStatus.ERROR
    assert submit.error is not None and submit.error.error_message == "нет денег"
    pay = await client.get_pay_result("c")
    assert pay.status is PayResultStatus.PART_EXEC and pay.count == 2
    assert pay.error is not None and pay.error.error_description == "частично"
    assert pay.payment_results[1].errors[0].field_name == "acc"
    receipts = await client.get_receipts_result("c")
    assert receipts.status is ReceiptsRequestStatus.FINISHED
    assert receipts.receipts[0].status is ReceiptStatus.SUCCESS
    assert receipts.receipts[0].sum == Decimal("1500.50")  # точный Decimal
    await client.aclose()


async def test_list_registries_secured_and_get_registry_regular():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        assert request.url.path.endswith("/payment-registry/list")
        body = json.loads(request.content)
        assert body["statuses"] == ["EXECUTED", "PART_EXEC"]
        return httpx.Response(
            200,
            content=(
                b'{"paymentOrders":[{"number":10,"date":"2026-06-01T10:00:00Z",'
                b'"count":3,"sum":4500.00,"status":"EXECUTED"}]}'
            ),
            headers={"content-type": "application/json"},
        )

    def reg(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        assert request.url.path.endswith("/payment-registry/987")
        return httpx.Response(
            200,
            content=(
                b'{"status":"PART_EXEC","paymentsCount":2,"totalSum":12345.67,'
                b'"payments":[{"number":1,"status":"EXECUTED",'
                b'"selfEmployedInfo":{"firstName":"\xd0\x98","lastName":"\xd0\x9f"},'
                b'"sum":12000.00,"collectionAmount":345.67}]}'
            ),
            headers={"content-type": "application/json"},
        )

    client = _client(reg, sec)
    lst = await client.list_payment_registries(
        ListRegistriesRequest(
            statuses=["EXECUTED", "PART_EXEC"],  # type: ignore[list-item]
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
        )
    )
    assert lst.payment_orders[0].sum == Decimal("4500.00")
    assert lst.payment_orders[0].created_at.year == 2026
    info = await client.get_payment_registry(987)
    assert info.total_sum == Decimal("12345.67")
    assert info.payments[0].status is PaymentInfoStatus.EXECUTED
    assert info.payments[0].collection_amount == Decimal("345.67")
    await client.aclose()


async def test_secured_methods_require_cert():
    client = _client(lambda r: httpx.Response(200, json={}))  # no secured transport
    with pytest.raises(MutualTLSRequiredError):
        await client.submit_payment_registry(1)
    with pytest.raises(MutualTLSRequiredError):
        await client.get_submit_result("c")
    with pytest.raises(MutualTLSRequiredError):
        await client.pay_payment_registry(1)
    with pytest.raises(MutualTLSRequiredError):
        await client.get_pay_result("c")
    with pytest.raises(MutualTLSRequiredError):
        await client.request_receipts(1)
    with pytest.raises(MutualTLSRequiredError):
        await client.get_receipts_result("c")
    with pytest.raises(MutualTLSRequiredError):
        await client.list_payment_registries(ListRegistriesRequest())
    await client.aclose()


async def test_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/recipients/list"):
            return httpx.Response(
                403,
                json={
                    "errorId": "e-1",
                    "errorCode": "NO_SCOPE",
                    "errorMessage": "нет прав",
                },
            )
        return httpx.Response(400, text="bad")

    client = _client(handler)
    with pytest.raises(ForbiddenError) as exc:
        await client.list_recipients(ListRecipientsRequest())
    assert exc.value.error_id == "e-1" and exc.value.code == "NO_SCOPE"
    with pytest.raises(ValidationError):
        await client.get_create_recipients_result("c")
    await client.aclose()


def test_client_construction_branches(monkeypatch):
    # Подменяем транспорты фейками — покрываем обе ветки __init__ без сети/сертификатов.
    a_calls: list = []
    s_calls: list = []

    class FakeAsync:
        def __init__(self, **kw):
            a_calls.append(kw)

    class FakeSync:
        def __init__(self, **kw):
            s_calls.append(kw)

    monkeypatch.setattr("tbank.core.transport.AsyncTransport", FakeAsync)
    monkeypatch.setattr("tbank.core.transport.SyncTransport", FakeSync)

    plain = SelfEmployedClient(token="x")
    assert plain._secured_transport is None
    assert a_calls[-1]["base_url"] == PROD_URL

    with_cert = SelfEmployedClient(token="x", cert=("c.pem", "k.pem"), sandbox=True)
    assert with_cert._secured_transport is not None
    assert a_calls[-1]["base_url"] == SANDBOX_SECURED_URL
    assert a_calls[-1]["cert"] == ("c.pem", "k.pem")

    sync_plain = SyncSelfEmployedClient(token="x")
    assert sync_plain._secured_transport is None
    sync_cert = SyncSelfEmployedClient(token="x", cert=("c.pem", "k.pem"))
    assert sync_cert._secured_transport is not None
    assert s_calls[-1]["base_url"] == SECURED_URL


# --- Sync-клиент: сквозной прогон ---


def test_sync_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"errorMessage": "bad"})

    client = SyncSelfEmployedClient(
        token="T", transport=_reg_transport(handler, sync=True)
    )
    with pytest.raises(ValidationError):
        client.list_recipients(ListRecipientsRequest())
    client.close()


def test_sync_client_end_to_end():
    def reg(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/recipients/create") or path.endswith(
            "/recipients/add/by-requisites"
        ):
            return httpx.Response(
                200,
                json={"correlationId": json.loads(request.content)["correlationId"]},
            )
        if path.endswith("/recipients/create/result") or path.endswith(
            "/by-requisites/result"
        ):
            return httpx.Response(200, json={"recipientResults": []})
        if path.endswith("/recipients/list"):
            return httpx.Response(200, json={"recipients": []})
        if path.endswith("/payment-registry/create"):
            return httpx.Response(
                200,
                json={"correlationId": json.loads(request.content)["correlationId"]},
            )
        if path.endswith("/payment-registry/create/result"):
            return httpx.Response(200, json={"status": "QUEUED"})
        if path.endswith("/payment-registry/987"):
            return httpx.Response(
                200, json={"status": "DRAFT", "paymentsCount": 0, "totalSum": 0}
            )
        raise AssertionError(path)

    def sec(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith(("/submit", "/pay", "/receipts")):
            return httpx.Response(
                200,
                json={"correlationId": json.loads(request.content)["correlationId"]},
            )
        if path.endswith("/submit/result"):
            return httpx.Response(
                200, json={"paymentRegistryId": 1, "status": "ACCEPTED"}
            )
        if path.endswith("/pay/result"):
            return httpx.Response(
                200, json={"paymentRegistryId": 1, "status": "SENT", "count": 1}
            )
        if path.endswith("/receipts/result"):
            return httpx.Response(200, json={"status": "IN_PROGRESS"})
        if path.endswith("/payment-registry/list"):
            return httpx.Response(200, json={"paymentOrders": []})
        raise AssertionError(path)

    client = SyncSelfEmployedClient(
        token="T",
        transport=_reg_transport(reg, sync=True),
        secured_transport=_sec_transport(sec, sync=True),
    )
    draft = RecipientDraft(
        number=1,
        first_name="И",
        last_name="П",
        birth_date=date(1990, 1, 2),
        birth_place="М",
        citizenship="РФ",
    )
    assert (
        client.create_recipients(
            CreateRecipientsRequest(recipients=[draft], correlation_id="a")
        )
        == "a"
    )
    assert client.get_create_recipients_result("a").recipient_results == []
    assert (
        client.add_recipients_by_requisites(
            AddRecipientsByRequisitesRequest(
                correlation_id="b",
                recipients=[
                    RecipientByRequisites(
                        number=1,
                        first_name="И",
                        last_name="П",
                        bank_info=RecipientBankInfo(account_number="1"),
                    )
                ],
            )
        )
        == "b"
    )
    assert client.get_add_recipients_result("b").recipient_results == []
    assert client.list_recipients(ListRecipientsRequest()).recipients == []
    assert (
        client.create_payment_registry(
            CreatePaymentRegistryRequest(
                correlation_id="c",
                payments=[
                    RegistryPayment(
                        number=1,
                        account_number="1",
                        payment_purpose="p",
                        self_employed_info=SelfEmployedInfo(
                            first_name="И", last_name="П"
                        ),
                        sum=Decimal("10"),
                    )
                ],
            )
        )
        == "c"
    )
    assert client.get_create_registry_result("c").status is DraftStatus.QUEUED
    assert client.submit_payment_registry(1, correlation_id="d") == "d"
    assert client.get_submit_result("d").status is SubmitResultStatus.ACCEPTED
    assert client.pay_payment_registry(1, correlation_id="e") == "e"
    assert client.get_pay_result("e").status is PayResultStatus.SENT
    uuid.UUID(client.request_receipts(1))  # без correlation_id → авто-генерация
    assert client.get_receipts_result("f").status is ReceiptsRequestStatus.IN_PROGRESS
    assert client.list_payment_registries(ListRegistriesRequest()).payment_orders == []
    assert client.get_payment_registry(987).status.value == "DRAFT"
    client.close()
