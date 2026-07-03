import json
import uuid
from datetime import date, datetime
from decimal import Decimal

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, MutualTLSRequiredError, ValidationError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.salary.aio import (
    PROD_URL,
    SANDBOX_SECURED_URL,
    SECURED_URL,
    SalaryClient,
)
from tbank.salary.enums import (
    AddressKind,
    CancelStatus,
    DocumentType,
    DraftStatus,
    EmployeeStatus,
    PaymentInfoStatus,
    PhoneType,
    RegistryStatus,
    RevenueTypeCode,
    SubmitResultStatus,
)
from tbank.salary.models import (
    AddEmployeesByRequisitesRequest,
    CreateEmployeesRequest,
    CreatePaymentRegistryRequest,
    CreateSubmitRegistryRequest,
    EmployeeAddress,
    EmployeeBankInfo,
    EmployeeByRequisites,
    EmployeeDocument,
    EmployeeDraft,
    EmployeePhone,
    JobInfo,
    ListEmployeesRequest,
    ListRegistriesRequest,
    PayRegistryRequest,
    RegistryEmployeeInfo,
    RegistryPayment,
)
from tbank.salary.sync import SalaryClient as SyncSalaryClient


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
    return SalaryClient(
        token="T",
        transport=_reg_transport(reg_handler),
        secured_transport=_sec_transport(sec_handler) if sec_handler else None,
    )


# --- Сотрудники (обычный хост) ---


async def test_add_employees_by_requisites_and_result_key():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        if request.method == "POST":
            body = json.loads(request.content)
            assert request.url.path == "/openapi/api/v1/employees/add/by-requisites"
            assert body["employees"][0]["bankInfo"]["accountNumber"] == "40817"
            return httpx.Response(200, json={"correlationId": body["correlationId"]})
        # результат: ключ "employeesResults"
        return httpx.Response(
            200,
            json={
                "employeesResults": [
                    {
                        "number": 1,
                        "firstName": "И",
                        "lastName": "П",
                        "employeeId": 7,
                        "status": "CREATED",
                    }
                ]
            },
        )

    client = _client(handler)
    cid = await client.add_employees_by_requisites(
        AddEmployeesByRequisitesRequest(
            correlation_id="c1",
            employees=[
                EmployeeByRequisites(
                    number=1,
                    first_name="И",
                    last_name="П",
                    bank_info=EmployeeBankInfo(account_number="40817"),
                )
            ],
        )
    )
    assert cid == "c1"
    res = await client.get_add_employees_result("c1")
    assert res.employees_results[0].employee_id == 7
    assert res.employees_results[0].status is DraftStatus.CREATED
    await client.aclose()


async def test_create_employees_full_draft_and_result_key():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={"correlationId": "auto"})
        # результат: ключ "employeeResults" (единственное число!)
        return httpx.Response(
            200,
            json={
                "employeeResults": [
                    {
                        "number": 1,
                        "firstName": "И",
                        "lastName": "П",
                        "status": "ERROR",
                        "errors": [{"fieldName": "inn", "errorDescription": "плохо"}],
                    }
                ]
            },
        )

    client = _client(handler)
    cid = await client.create_employees(
        CreateEmployeesRequest(
            employees=[
                EmployeeDraft(
                    number=1,
                    first_name="Иван",
                    last_name="Петров",
                    birth_date=date(1990, 1, 2),
                    birth_place="Москва",
                    citizenship="РФ",
                    job_info=JobInfo(position="Инженер"),
                    phones=[EmployeePhone(type=PhoneType.WORK, number="+7")],
                    addresses=[
                        EmployeeAddress(
                            type=AddressKind.WORK, postal_code="101000", state="Москва"
                        )
                    ],
                    documents=[
                        EmployeeDocument(
                            type=DocumentType.PASSPORT,
                            serial="4500",
                            issued_on=date(2010, 3, 4),
                            organization="ОВД",
                        )
                    ],
                )
            ]
        )
    )
    uuid.UUID(cid)  # авто-correlationId
    b = seen["body"]["employees"][0]
    assert b["jobInfo"]["position"] == "Инженер"
    assert b["addresses"][0]["type"] == "Работы"
    assert b["documents"][0]["date"] == "2010-03-04"
    res = await client.get_create_employees_result("x")
    assert res.employee_results[0].status is DraftStatus.ERROR
    assert res.employee_results[0].errors[0].field_name == "inn"
    await client.aclose()


async def test_list_employees():
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {"employeeIds": [7, 8]}
        return httpx.Response(
            200,
            json={
                "employees": [
                    {
                        "id": 7,
                        "status": "FIRED",
                        "firstName": "И",
                        "lastName": "П",
                        "bankInfo": {
                            "accountNumber": "40817",
                            "agreementNumber": "A-1",
                        },
                        "jobInfo": {"position": "Инженер"},
                        "phones": [{"type": "Мобильный", "number": "+7"}],
                    }
                ]
            },
        )

    client = _client(handler)
    res = await client.list_employees(ListEmployeesRequest(employee_ids=[7, 8]))
    e = res.employees[0]
    assert e.status is EmployeeStatus.FIRED
    assert e.bank_info.agreement_number == "A-1"
    assert e.job_info is not None and e.job_info.position == "Инженер"
    assert e.phones is not None and e.phones[0].type is PhoneType.MOBILE
    await client.aclose()


# --- Реестр: создание (обычный) + карточка (обычный) ---


async def test_create_registry_number_and_get_card():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        if request.method == "POST" and request.url.path.endswith("/create"):
            seen["body"] = json.loads(request.content)
            return httpx.Response(
                200, json={"correlationId": seen["body"]["correlationId"]}
            )
        if request.url.path.endswith("/create/result"):
            return httpx.Response(
                200, json={"paymentRegistryId": 55, "status": "QUEUED"}
            )
        # карточка
        assert request.url.path.endswith("/payment-registry/55")
        return httpx.Response(
            200,
            content=(
                b'{"status":"PART_EXEC","paymentsCount":1,"totalSum":50000.75,'
                b'"companyAccountNumber":"40702","payments":[{"number":1,"status":"EXECUTED",'
                b'"employeeInfo":{"firstName":"\xd0\x98","lastName":"\xd0\x9f","employeeId":7},'
                b'"sum":50000.75,"periodStart":"2026-06-01","periodEnd":"2026-06-30"}]}'
            ),
            headers={"content-type": "application/json"},
        )

    client = _client(handler)
    cid = await client.create_payment_registry(
        CreatePaymentRegistryRequest(
            correlation_id="c2",
            company_account_number="40702",
            payments=[
                RegistryPayment(
                    number=1,
                    account_number="40817",
                    payment_purpose="Зарплата за июнь",
                    employee_info=RegistryEmployeeInfo(
                        first_name="Иван", last_name="Петров", employee_id=7
                    ),
                    sum=Decimal("50000.75"),
                    period_start=date(2026, 6, 1),
                    period_end=date(2026, 6, 30),
                    revenue_type_code=RevenueTypeCode.CODE_1,
                )
            ],
        )
    )
    assert cid == "c2"
    assert seen["body"]["payments"][0]["sum"] == 50000.75
    assert seen["body"]["payments"][0]["periodStart"] == "2026-06-01"
    created = await client.get_create_registry_result("c2")
    assert created.payment_registry_id == 55 and created.status is DraftStatus.QUEUED
    info = await client.get_payment_registry(55)
    assert info.total_sum == Decimal("50000.75")
    assert info.payments[0].status is PaymentInfoStatus.EXECUTED
    assert info.payments[0].employee_info.employee_id == 7
    await client.aclose()


# --- Реестр: secured (mTLS) ---


async def test_create_submit_submit_cancel_route_secured():
    calls = []

    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        path = request.url.path
        calls.append(path)
        body = json.loads(request.content)
        if path.endswith("/create-submit"):
            assert body["payments"][0]["sum"] == 100.0
            return httpx.Response(200, json={"correlationId": body["correlationId"]})
        if path.endswith("/submit"):
            assert body == {"paymentRegistryId": 55, "correlationId": "cs"}
            return httpx.Response(200, json={"correlationId": body["correlationId"]})
        if path.endswith("/cancel"):
            assert body["paymentOrderNumber"] == 9
            return httpx.Response(200, json={"correlationId": body["correlationId"]})
        raise AssertionError(path)

    def reg(request: httpx.Request) -> httpx.Response:
        raise AssertionError("secured method hit regular host")

    client = _client(reg, sec)
    cs = await client.create_and_submit_registry(
        CreateSubmitRegistryRequest(
            correlation_id="cs0",
            load_date=datetime(2026, 6, 1),
            payments=[
                RegistryPayment(
                    number=1,
                    account_number="40817",
                    payment_purpose="p",
                    employee_info=RegistryEmployeeInfo(first_name="И", last_name="П"),
                    sum=Decimal("100"),
                )
            ],
        )
    )
    assert cs == "cs0"
    assert await client.submit_payment_registry(55, correlation_id="cs") == "cs"
    cancel_cid = await client.cancel_payment_registry(9)  # авто-correlationId
    uuid.UUID(cancel_cid)
    assert any(p.endswith("/create-submit") for p in calls)
    await client.aclose()


async def test_secured_results_and_pay():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        path = request.url.path
        if path.endswith("/create-submit/result"):
            return httpx.Response(
                200,
                json={
                    "paymentRegistryId": 55,
                    "status": "ACCEPTED",
                    "paymentErrors": [
                        {
                            "number": 1,
                            "accountNumber": "40817",
                            "errors": [{"fieldName": "sum", "errorDescription": "x"}],
                        }
                    ],
                },
            )
        if path.endswith("/submit/result"):
            return httpx.Response(
                200,
                json={
                    "paymentRegistryId": 55,
                    "status": "ERROR",
                    "error": {"errorCode": "E1", "errorMessage": "нет денег"},
                },
            )
        if path.endswith("/cancel/result"):
            return httpx.Response(
                200,
                json={
                    "status": "ERROR",
                    "error": {"errorCode": "E2", "errorDescription": "поздно"},
                },
            )
        # pay
        assert path == "/api/v1/payment/payment-registry/pay"
        body = json.loads(request.content)
        assert body["paymentRegistryId"] == 55 and body["accountNumber"] == "40702"
        assert "id" in body
        return httpx.Response(200, json={})

    client = _client(lambda r: httpx.Response(500), sec)
    cs = await client.get_create_submit_result("c")
    assert cs.status is SubmitResultStatus.ACCEPTED
    assert cs.payment_errors[0].errors[0].field_name == "sum"
    sub = await client.get_submit_result("c")
    assert sub.status is SubmitResultStatus.ERROR
    assert sub.error is not None and sub.error.error_message == "нет денег"
    can = await client.get_cancel_result("c")
    assert can.status is CancelStatus.ERROR
    assert can.error is not None and can.error.error_description == "поздно"
    pay_id = await client.pay_payment_registry(
        PayRegistryRequest(payment_registry_id=55, account_number="40702", purpose="ЗП")
    )
    uuid.UUID(pay_id)  # id — авто ключ идемпотентности
    await client.aclose()


async def test_list_registries_secured():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        assert request.url.path.endswith("/payment-registry/list")
        assert json.loads(request.content)["statuses"] == ["EXECUTED"]
        return httpx.Response(
            200,
            content=(
                b'{"paymentOrders":[{"number":10,"date":"2026-06-01T10:00:00Z",'
                b'"count":3,"sum":150000.00,"status":"EXECUTED"}]}'
            ),
            headers={"content-type": "application/json"},
        )

    client = _client(lambda r: httpx.Response(500), sec)
    res = await client.list_payment_registries(
        ListRegistriesRequest(
            statuses=[RegistryStatus.EXECUTED], period_start=date(2026, 1, 1)
        )
    )
    assert res.payment_orders[0].sum == Decimal("150000.00")
    assert res.payment_orders[0].created_at.year == 2026
    await client.aclose()


async def test_secured_methods_require_cert():
    client = _client(lambda r: httpx.Response(200, json={}))
    with pytest.raises(MutualTLSRequiredError):
        await client.create_and_submit_registry(
            CreateSubmitRegistryRequest(
                payments=[
                    RegistryPayment(
                        number=1,
                        account_number="1",
                        payment_purpose="p",
                        employee_info=RegistryEmployeeInfo(
                            first_name="И", last_name="П"
                        ),
                        sum=Decimal("1"),
                    )
                ]
            )
        )
    with pytest.raises(MutualTLSRequiredError):
        await client.submit_payment_registry(1)
    with pytest.raises(MutualTLSRequiredError):
        await client.get_submit_result("c")
    with pytest.raises(MutualTLSRequiredError):
        await client.pay_payment_registry(
            PayRegistryRequest(payment_registry_id=1, account_number="1", purpose="p")
        )
    with pytest.raises(MutualTLSRequiredError):
        await client.cancel_payment_registry(1)
    with pytest.raises(MutualTLSRequiredError):
        await client.get_cancel_result("c")
    with pytest.raises(MutualTLSRequiredError):
        await client.get_create_submit_result("c")
    with pytest.raises(MutualTLSRequiredError):
        await client.list_payment_registries(ListRegistriesRequest())
    await client.aclose()


async def test_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/employees/list"):
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
        await client.list_employees(ListEmployeesRequest(employee_ids=[1]))
    assert exc.value.error_id == "e-1"
    with pytest.raises(ValidationError):
        await client.get_create_registry_result("c")
    await client.aclose()


def test_client_construction_branches(monkeypatch):
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

    plain = SalaryClient(token="x")
    assert plain._secured_transport is None
    assert a_calls[-1]["base_url"] == PROD_URL
    with_cert = SalaryClient(token="x", cert=("c.pem", "k.pem"), sandbox=True)
    assert with_cert._secured_transport is not None
    assert a_calls[-1]["base_url"] == SANDBOX_SECURED_URL
    assert a_calls[-1]["cert"] == ("c.pem", "k.pem")

    sync_plain = SyncSalaryClient(token="x")
    assert sync_plain._secured_transport is None
    sync_cert = SyncSalaryClient(token="x", cert=("c.pem", "k.pem"))
    assert sync_cert._secured_transport is not None
    assert s_calls[-1]["base_url"] == SECURED_URL


def test_sync_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"errorMessage": "bad"})

    client = SyncSalaryClient(token="T", transport=_reg_transport(handler, sync=True))
    with pytest.raises(ValidationError):
        client.list_employees(ListEmployeesRequest(employee_ids=[1]))
    client.close()


def test_sync_client_end_to_end():
    def reg(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith(
            ("/by-requisites", "/employees/create", "/payment-registry/create")
        ):
            return httpx.Response(
                200,
                json={"correlationId": json.loads(request.content)["correlationId"]},
            )
        if path.endswith("/by-requisites/result"):
            return httpx.Response(200, json={"employeesResults": []})
        if path.endswith("/employees/create/result"):
            return httpx.Response(200, json={"employeeResults": []})
        if path.endswith("/employees/list"):
            return httpx.Response(200, json={"employees": []})
        if path.endswith("/payment-registry/create/result"):
            return httpx.Response(200, json={"status": "CREATED"})
        if path.endswith("/payment-registry/55"):
            return httpx.Response(
                200, json={"status": "DRAFT", "paymentsCount": 0, "totalSum": 0}
            )
        raise AssertionError(path)

    def sec(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith(("/create-submit", "/submit", "/cancel")):
            return httpx.Response(
                200,
                json={"correlationId": json.loads(request.content)["correlationId"]},
            )
        if path.endswith("/payment/payment-registry/pay"):
            return httpx.Response(200, json={})
        if path.endswith("/create-submit/result"):
            return httpx.Response(200, json={"status": "ACCEPTED"})
        if path.endswith("/submit/result"):
            return httpx.Response(
                200, json={"paymentRegistryId": 1, "status": "ACCEPTED"}
            )
        if path.endswith("/cancel/result"):
            return httpx.Response(200, json={"status": "DONE"})
        if path.endswith("/payment-registry/list"):
            return httpx.Response(200, json={"paymentOrders": []})
        raise AssertionError(path)

    client = SyncSalaryClient(
        token="T",
        transport=_reg_transport(reg, sync=True),
        secured_transport=_sec_transport(sec, sync=True),
    )
    emp = EmployeeByRequisites(
        number=1,
        first_name="И",
        last_name="П",
        bank_info=EmployeeBankInfo(account_number="1"),
    )
    assert (
        client.add_employees_by_requisites(
            AddEmployeesByRequisitesRequest(correlation_id="a", employees=[emp])
        )
        == "a"
    )
    assert client.get_add_employees_result("a").employees_results == []
    draft = EmployeeDraft(
        number=1,
        first_name="И",
        last_name="П",
        birth_date=date(1990, 1, 2),
        birth_place="М",
        citizenship="РФ",
        job_info=JobInfo(position="p"),
    )
    assert (
        client.create_employees(
            CreateEmployeesRequest(correlation_id="b", employees=[draft])
        )
        == "b"
    )
    assert client.get_create_employees_result("b").employee_results == []
    assert client.list_employees(ListEmployeesRequest(employee_ids=[1])).employees == []
    pay = RegistryPayment(
        number=1,
        account_number="1",
        payment_purpose="p",
        employee_info=RegistryEmployeeInfo(first_name="И", last_name="П"),
        sum=Decimal("10"),
    )
    assert (
        client.create_payment_registry(
            CreatePaymentRegistryRequest(correlation_id="c", payments=[pay])
        )
        == "c"
    )
    assert client.get_create_registry_result("c").status is DraftStatus.CREATED
    assert (
        client.create_and_submit_registry(
            CreateSubmitRegistryRequest(correlation_id="d", payments=[pay])
        )
        == "d"
    )
    assert client.get_create_submit_result("d").status is SubmitResultStatus.ACCEPTED
    assert client.submit_payment_registry(1, correlation_id="e") == "e"
    assert client.get_submit_result("e").status is SubmitResultStatus.ACCEPTED
    pid = client.pay_payment_registry(
        PayRegistryRequest(
            payment_registry_id=1, account_number="1", purpose="p", id="pay-1"
        )
    )
    assert pid == "pay-1"
    assert client.cancel_payment_registry(9, correlation_id="f") == "f"
    assert client.get_cancel_result("f").status is CancelStatus.DONE
    assert client.list_payment_registries(ListRegistriesRequest()).payment_orders == []
    assert client.get_payment_registry(55).status.value == "DRAFT"
    client.close()
