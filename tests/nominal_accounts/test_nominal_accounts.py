import json
from decimal import Decimal

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import (
    ForbiddenError,
    MutualTLSRequiredError,
    TBankAPIError,
    ValidationError,
)
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.nominal_accounts.aio import (
    PROD_URL,
    SANDBOX_URL,
    SECURED_URL,
    NominalAccountsClient,
)
from tbank.nominal_accounts.enums import DealStatus, PaymentStatus, StepStatus
from tbank.nominal_accounts.models import (
    AddCardRequest,
    Address,
    AmountDistributionItem,
    BeneficiaryFlResidentRequest,
    BeneficiaryFlResidentResponse,
    CardBankDetailsResponse,
    CreateRegularPaymentRequest,
    CreateTaxPaymentRequest,
    CreateTransferRequest,
    DealRequest,
    DeponentRequest,
    FailedAddCardResponse,
    IdentifyIncomingTransactionRequest,
    Passport,
    PendingAddCardResponse,
    RecipientRequest,
    RegularPaymentResponse,
    RkcBankDetailsRequest,
    ScoringSucceeded,
    StepRequest,
    TaxPaymentParameters,
    TaxPaymentResponse,
    TransferParty,
    UpdateRecipientBankDetailsRequest,
)
from tbank.nominal_accounts.sync import NominalAccountsClient as SyncClient


def _transport(handler, base_url, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=base_url, client=client, auth=BearerAuth("T"))


def _client(reg_handler, sec_handler=None):
    return NominalAccountsClient(
        token="T",
        transport=_transport(reg_handler, PROD_URL),
        secured_transport=(
            _transport(sec_handler, SECURED_URL) if sec_handler else None
        ),
    )


def _sync_client(reg_handler, sec_handler=None):
    return SyncClient(
        token="T",
        transport=_transport(reg_handler, PROD_URL, sync=True),
        secured_transport=(
            _transport(sec_handler, SECURED_URL, sync=True) if sec_handler else None
        ),
    )


def _fl_beneficiary():
    return BeneficiaryFlResidentRequest(
        first_name="Иван",
        last_name="Петров",
        is_self_employed=True,
        birth_date="1990-05-01",
        citizenship="RU",
        documents=[
            Passport(
                serial="4509",
                number="123456",
                issued_on="2010-06-01",
                division="770-001",
            )
        ],
        addresses=[Address(type="REGISTRATION_ADDRESS", address="Москва")],
    )


# --- Бенефициары ---


async def test_create_beneficiary_discriminated_and_idempotency():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/openapi/api/v1/nominal-accounts/beneficiaries"
        assert request.headers.get("Idempotency-Key")  # автогенерация ключа
        body = json.loads(request.content)
        assert body["type"] == "FL_RESIDENT"
        assert body["documents"][0]["type"] == "PASSPORT"
        assert body["documents"][0]["date"] == "2010-06-01"
        return httpx.Response(
            201,
            json={
                "type": "FL_RESIDENT",
                "beneficiaryId": "b-1",
                "firstName": "Иван",
                "lastName": "Петров",
                "isSelfEmployed": True,
                "birthDate": "1990-05-01",
            },
        )

    client = _client(handler)
    result = await client.create_beneficiary(_fl_beneficiary())
    assert isinstance(result, BeneficiaryFlResidentResponse)
    assert result.beneficiary_id == "b-1"


async def test_create_beneficiary_explicit_idempotency_key():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["key"] = request.headers.get("Idempotency-Key")
        return httpx.Response(201, json={"type": "LITE_CONTACT", "beneficiaryId": "b"})

    client = _client(handler)
    await client.create_beneficiary(_fl_beneficiary(), idempotency_key="fixed-key")
    assert captured["key"] == "fixed-key"


async def test_list_beneficiaries_pagination_params():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("offset") == "10"
        assert request.url.params.get("limit") == "50"
        return httpx.Response(
            200,
            json={
                "offset": 10,
                "limit": 50,
                "size": 1,
                "total": 1,
                "results": [
                    {"type": "LITE_CONTACT", "beneficiaryId": "b-2"},
                ],
            },
        )

    client = _client(handler)
    page = await client.list_beneficiaries(offset=10, limit=50)
    assert page.total == 1
    assert page.results[0].beneficiary_id == "b-2"


async def test_get_and_update_beneficiary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openapi/api/v1/nominal-accounts/beneficiaries/b-9"
        return httpx.Response(
            200,
            json={
                "type": "FL_RESIDENT",
                "beneficiaryId": "b-9",
                "firstName": "И",
                "lastName": "П",
                "isSelfEmployed": False,
                "birthDate": "1990-05-01",
            },
        )

    client = _client(handler)
    got = await client.get_beneficiary("b-9")
    assert got.beneficiary_id == "b-9"
    upd = await client.update_beneficiary("b-9", _fl_beneficiary())
    assert isinstance(upd, BeneficiaryFlResidentResponse)


# --- Реквизиты для добавления карты ---


async def test_add_card_request_pending_and_failed_unions():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.path.endswith("/beneficiaries/b/add-card-requests")
            return httpx.Response(
                201,
                json={
                    "status": "PENDING",
                    "beneficiaryId": "b",
                    "addCardRequestId": "acr-1",
                    "terminalKey": "TK",
                    "addCardUrl": "https://pay",
                },
            )
        return httpx.Response(
            200,
            json={
                "status": "FAILED",
                "beneficiaryId": "b",
                "addCardRequestId": "acr-1",
                "terminalKey": "TK",
                "errorMessage": "denied",
            },
        )

    client = _client(handler)
    created = await client.create_add_card_request(
        "b", AddCardRequest(terminal_key="TK")
    )
    assert isinstance(created, PendingAddCardResponse)
    assert created.add_card_url == "https://pay"
    status = await client.get_add_card_request("b", "acr-1")
    assert isinstance(status, FailedAddCardResponse)
    assert status.error_message == "denied"


# --- Банковские реквизиты ---


async def test_bank_details_crud_union_and_delete():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE":
            return httpx.Response(200, json={})
        if request.method == "POST" and request.url.path.endswith("/set-default"):
            return httpx.Response(200, json={})
        if request.method == "POST":
            body = json.loads(request.content)
            assert body["type"] == "PAYMENT_DETAILS"
            assert body["bik"] == "044525225"
        return httpx.Response(
            201,
            json={
                "type": "CARD",
                "beneficiaryId": "b",
                "bankDetailsId": "bd-1",
                "cardId": "c-1",
                "terminalKey": "TK",
            },
        )

    client = _client(handler)
    created = await client.create_bank_details(
        "b",
        RkcBankDetailsRequest(
            bik="044525225",
            bank_name="Т-Банк",
            account_number="40817810000000000001",
            corr_account_number="30101810000000000225",
        ),
    )
    assert isinstance(created, CardBankDetailsResponse)
    assert created.bank_details_id == "bd-1"
    assert await client.delete_bank_details("b", "bd-1") is None
    assert await client.set_default_bank_details("b", "bd-1") is None


async def test_scoring_query_params_and_union():
    def handler(request: httpx.Request) -> httpx.Response:
        assert (
            request.url.path == "/openapi/api/v2/nominal-accounts/beneficiaries/scoring"
        )
        assert request.url.params.get("passed") == "true"
        assert request.url.params.get("beneficiaryId") == "b-3"
        return httpx.Response(
            200,
            json={
                "offset": 0,
                "limit": 10,
                "size": 1,
                "total": 1,
                "results": [
                    {"status": "SUCCEEDED", "beneficiaryId": "b-3", "warnings": []},
                ],
            },
        )

    client = _client(handler)
    page = await client.get_beneficiaries_scoring(beneficiary_id="b-3", passed=True)
    assert isinstance(page.results[0], ScoringSucceeded)


# --- Сделки и этапы ---


async def test_deal_lifecycle_and_secured_routing():
    def reg(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        if request.url.path.endswith("/deals") and request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "dealId": "d-1",
                    "accountNumber": "40817810000000000001",
                    "status": "DRAFT",
                },
            )
        return httpx.Response(200, json={})

    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        if request.url.path.endswith("/is-valid"):
            return httpx.Response(
                200, json={"isValid": False, "reasons": [{"code": "E1"}]}
            )
        return httpx.Response(
            200,
            json={
                "dealId": "d-1",
                "accountNumber": "40817810000000000001",
                "status": "ACCEPTED",
            },
        )

    client = _client(reg, sec)
    created = await client.create_deal(
        DealRequest(account_number="40817810000000000001")
    )
    assert created.deal_id == "d-1"
    assert created.status == DealStatus.DRAFT
    got = await client.get_deal("d-1")  # secured
    assert got.status == DealStatus.ACCEPTED
    validity = await client.get_deal_validity("d-1")  # secured
    assert validity.is_valid is False
    assert validity.reasons[0].code == "E1"
    assert await client.accept_deal("d-1") is None
    assert await client.cancel_deal("d-1") is None
    assert await client.draft_deal("d-1") is None
    assert await client.delete_deal("d-1") is None


async def test_step_create_and_get_secured():
    def reg(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={
                "dealId": "d-1",
                "stepId": "s-1",
                "stepNumber": 1,
                "description": "Первый этап",
                "status": "NEW",
            },
        )

    def sec(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "dealId": "d-1",
                "stepId": "s-1",
                "stepNumber": 1,
                "description": "Первый этап",
                "status": "COMPLETED",
            },
        )

    client = _client(reg, sec)
    created = await client.create_step("d-1", StepRequest(description="Первый этап"))
    assert created.status == StepStatus.NEW
    got = await client.get_step("d-1", "s-1")  # secured
    assert got.status == StepStatus.COMPLETED


# --- Депоненты и реципиенты ---


async def test_deponent_and_recipient_amounts_decimal():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        if request.url.path.endswith("/deponents/b"):
            assert body["amount"] == 1500.5
            return httpx.Response(
                200,
                json={
                    "dealId": "d",
                    "stepId": "s",
                    "beneficiaryId": "b",
                    "amount": 1500.50,
                },
            )
        if request.url.path.endswith("/recipients"):
            assert body["beneficiaryId"] == "b"
            return httpx.Response(
                201,
                json={
                    "dealId": "d",
                    "stepId": "s",
                    "beneficiaryId": "b",
                    "recipientId": "r-1",
                    "amount": 999.99,
                    "tax": 13.00,
                },
            )
        return httpx.Response(200, json={})

    client = _client(handler)
    dep = await client.set_deponent(
        "d", "s", "b", DeponentRequest(amount=Decimal("1500.50"))
    )
    assert dep.amount == Decimal("1500.50")
    rec = await client.create_recipient(
        "d",
        "s",
        RecipientRequest(
            beneficiary_id="b", amount=Decimal("999.99"), tax=Decimal("13")
        ),
    )
    assert rec.amount == Decimal("999.99")
    assert rec.tax == Decimal("13.00")


async def test_update_recipient_bank_details_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/recipients/r-1/update-bank-details")
        body = json.loads(request.content)
        assert body["bankDetailsId"] == "bd-2"
        return httpx.Response(200, json={})

    client = _client(handler)
    out = await client.update_recipient_bank_details(
        "d", "s", "r-1", UpdateRecipientBankDetailsRequest(bank_details_id="bd-2")
    )
    assert out is None


# --- Платежи ---


async def test_create_regular_and_tax_payment_unions():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["type"] == "REGULAR":
            return httpx.Response(
                201,
                json={
                    "type": "REGULAR",
                    "paymentId": "p-1",
                    "beneficiaryId": "b",
                    "accountNumber": "40817810000000000001",
                    "bankDetails": {"type": "CARD", "cardId": "c", "terminalKey": "TK"},
                    "amount": 100.00,
                    "status": "SUCCEEDED",
                    "purpose": "оплата",
                },
            )
        assert body["tax"]["kbk"] == "182"
        return httpx.Response(
            201,
            json={
                "type": "TAX",
                "paymentId": "p-2",
                "beneficiaryId": "b",
                "accountNumber": "40817810000000000001",
                "bankDetails": {
                    "type": "PAYMENT_DETAILS",
                    "bik": "044525225",
                    "bankName": "Т-Банк",
                    "accountNumber": "40817810000000000001",
                    "corrAccountNumber": "30101810000000000225",
                },
                "amount": 50.00,
                "status": "PENDING",
                "purpose": "налог",
                "uin": "0",
                "tax": {
                    "payerStatus": "01",
                    "kbk": "182",
                    "oktmo": "45000000",
                    "evidence": "ТП",
                    "period": "МС.01.2026",
                    "docNumber": "0",
                    "docDate": "0",
                },
            },
        )

    client = _client(handler)
    reg = await client.create_payment(
        CreateRegularPaymentRequest(
            beneficiary_id="b",
            account_number="40817810000000000001",
            amount=Decimal("100"),
            purpose="оплата",
        )
    )
    assert isinstance(reg, RegularPaymentResponse)
    assert reg.status == PaymentStatus.SUCCEEDED
    tax = await client.create_payment(
        CreateTaxPaymentRequest(
            beneficiary_id="b",
            account_number="40817810000000000001",
            bank_details={
                "type": "PAYMENT_DETAILS",
                "bik": "044525225",
                "bankName": "Т-Банк",
                "accountNumber": "40817810000000000001",
                "corrAccountNumber": "30101810000000000225",
            },
            amount=Decimal("50"),
            purpose="налог",
            uin="0",
            tax=TaxPaymentParameters(
                payer_status="01",
                kbk="182",
                oktmo="45000000",
                evidence="ТП",
                period="МС.01.2026",
                doc_number="0",
                doc_date="0",
            ),
        )
    )
    assert isinstance(tax, TaxPaymentResponse)
    assert tax.uin == "0"


async def test_get_payment_secured_and_retry():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        return httpx.Response(
            200,
            json={
                "type": "REGULAR",
                "paymentId": "p-1",
                "beneficiaryId": "b",
                "accountNumber": "40817810000000000001",
                "bankDetails": {
                    "type": "SBP",
                    "phoneNumber": "+7900",
                    "bankId": "1",
                    "terminalKey": "TK",
                },
                "amount": 100.00,
                "status": "FAILED",
                "purpose": "x",
            },
        )

    def reg(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/payments/p-1/retry")
        return httpx.Response(200, json={"retryPaymentId": "p-9"})

    client = _client(reg, sec)
    got = await client.get_payment("p-1")
    assert got.status == PaymentStatus.FAILED
    retried = await client.retry_payment("p-1")
    assert retried.retry_payment_id == "p-9"


# --- Пополнения и виртуальные счета ---


async def test_incoming_transactions_and_identify():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.path.endswith("/incoming-transactions/op-1/identify")
            body = json.loads(request.content)
            assert body["amountDistribution"][0]["amount"] == 10.0
            return httpx.Response(200, json={})
        return httpx.Response(
            200,
            json={
                "offset": 0,
                "limit": 10,
                "size": 1,
                "total": 1,
                "results": [
                    {
                        "accountNumber": "40817810000000000001",
                        "operationId": "op-1",
                        "amount": 500.25,
                    }
                ],
            },
        )

    client = _client(handler)
    page = await client.list_incoming_transactions(
        account_number="40817810000000000001"
    )
    assert page.results[0].amount == Decimal("500.25")
    out = await client.identify_incoming_transaction(
        "op-1",
        IdentifyIncomingTransactionRequest(
            amount_distribution=[
                AmountDistributionItem(beneficiary_id="b", amount=Decimal("10"))
            ]
        ),
    )
    assert out is None


async def test_balances_and_holds():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/balances"):
            return httpx.Response(
                200,
                json={
                    "offset": 0,
                    "limit": 10,
                    "size": 1,
                    "total": 1,
                    "results": [
                        {
                            "beneficiaryId": "b",
                            "accountNumber": "40817810000000000001",
                            "amount": 1000.00,
                            "amountOnHold": 250.00,
                        }
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "offset": 0,
                "limit": 10,
                "size": 1,
                "total": 1,
                "results": [
                    {
                        "beneficiaryId": "b",
                        "accountNumber": "40817810000000000001",
                        "holdId": "h-1",
                        "amount": 250.00,
                    }
                ],
            },
        )

    client = _client(handler)
    balances = await client.list_balances(account_number="40817810000000000001")
    assert balances.results[0].amount_on_hold == Decimal("250.00")
    holds = await client.list_holds(beneficiary_id="b")
    assert holds.results[0].hold_id == "h-1"


async def test_transfers_secured_and_from_alias():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        if request.method == "POST":
            body = json.loads(request.content)
            assert body["from"]["beneficiaryId"] == "a"
            assert body["to"]["beneficiaryId"] == "z"
            return httpx.Response(
                201,
                json={
                    "type": "DIRECT",
                    "transferId": "t-1",
                    "accountNumber": "40817810000000000001",
                    "from": {"beneficiaryId": "a"},
                    "to": {"beneficiaryId": "z"},
                    "amount": 300.00,
                },
            )
        if request.url.path.endswith("/transfers/t-1"):
            return httpx.Response(
                200,
                json={
                    "transferId": "t-1",
                    "accountNumber": "40817810000000000001",
                    "from": {"beneficiaryId": "a"},
                    "to": {"beneficiaryId": "z"},
                    "amount": 300.00,
                },
            )
        assert request.url.params.get("accountNumber") == "40817810000000000001"
        return httpx.Response(
            200,
            json={"offset": 0, "limit": 10, "size": 0, "total": 0, "results": []},
        )

    client = _client(lambda r: httpx.Response(500), sec)
    created = await client.create_transfer(
        CreateTransferRequest(
            account_number="40817810000000000001",
            from_=TransferParty(beneficiary_id="a"),
            to=TransferParty(beneficiary_id="z"),
            amount=Decimal("300"),
        )
    )
    assert created.transfer_id == "t-1"
    assert created.from_.beneficiary_id == "a"
    got = await client.get_transfer("t-1")
    assert got.to.beneficiary_id == "z"
    page = await client.list_transfers("40817810000000000001")
    assert page.total == 0


# --- mTLS и ошибки ---


async def test_secured_without_cert_raises():
    client = _client(lambda r: httpx.Response(200, json={}))
    with pytest.raises(MutualTLSRequiredError):
        await client.get_deal("d-1")
    with pytest.raises(MutualTLSRequiredError):
        await client.create_transfer(
            CreateTransferRequest(
                account_number="40817810000000000001",
                from_=TransferParty(beneficiary_id="a"),
                to=TransferParty(beneficiary_id="z"),
                amount=Decimal("1"),
            )
        )


async def test_error_mapping():
    def forbidden(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={"errorId": "e1", "errorMessage": "no access", "errorCode": "403"},
        )

    client = _client(forbidden)
    with pytest.raises(ForbiddenError) as exc:
        await client.list_beneficiaries()
    assert exc.value.error_id == "e1"

    def bad(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"errorId": "e2", "errorMessage": "bad", "errorCode": "V1"},
        )

    client = _client(bad)
    with pytest.raises(ValidationError) as exc2:
        await client.list_deals()
    assert exc2.value.code == "V1"


async def test_error_non_json_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream boom")

    client = _client(handler)
    with pytest.raises(TBankAPIError) as exc:
        await client.list_holds()
    assert exc.value.code == "500"
    assert "boom" in exc.value.message


# --- Синхронный клиент ---


def test_sync_client_parity():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Idempotency-Key")
        return httpx.Response(
            201,
            json={
                "dealId": "d-1",
                "accountNumber": "40817810000000000001",
                "status": "DRAFT",
            },
        )

    client = _sync_client(handler)
    created = client.create_deal(DealRequest(account_number="40817810000000000001"))
    assert created.deal_id == "d-1"
    client.close()


_ACC = "40817810000000000001"


def _sync_surface_handler(request: httpx.Request) -> httpx.Response:
    """Диспетчер валидных ответов для всех эндпоинтов — для sync smoke-теста."""
    p, m = request.url.path, request.method
    ben = {"type": "LITE_CONTACT", "beneficiaryId": "b"}
    bd = {
        "type": "SBP",
        "beneficiaryId": "b",
        "bankDetailsId": "bd",
        "phoneNumber": "+7900",
        "bankId": "1",
        "terminalKey": "TK",
    }
    deal = {"dealId": "d", "accountNumber": _ACC, "status": "DRAFT"}
    step = {
        "dealId": "d",
        "stepId": "s",
        "stepNumber": 1,
        "description": "x",
        "status": "NEW",
    }
    dep = {"dealId": "d", "stepId": "s", "beneficiaryId": "b", "amount": 1}
    rec = {
        "dealId": "d",
        "stepId": "s",
        "beneficiaryId": "b",
        "recipientId": "r",
        "amount": 1,
    }
    pay = {
        "type": "REGULAR",
        "paymentId": "p",
        "beneficiaryId": "b",
        "accountNumber": _ACC,
        "bankDetails": {"type": "CARD", "cardId": "c", "terminalKey": "TK"},
        "amount": 1,
        "status": "PENDING",
        "purpose": "x",
    }
    acr = {
        "status": "READY",
        "beneficiaryId": "b",
        "addCardRequestId": "acr",
        "terminalKey": "TK",
        "bankDetailsId": "bd",
    }
    transfer = {
        "transferId": "t",
        "accountNumber": _ACC,
        "from": {"beneficiaryId": "a"},
        "to": {"beneficiaryId": "z"},
        "amount": 1,
    }

    def paged(item):
        return {"offset": 0, "limit": 10, "size": 1, "total": 1, "results": [item]}

    if m == "DELETE":
        body = {}
    elif p.endswith(
        (
            "/set-default",
            "/accept",
            "/cancel",
            "/draft",
            "/complete",
            "/update-bank-details",
            "/identify",
        )
    ):
        body = {}
    elif p.endswith("/retry"):
        body = {"retryPaymentId": "rp"}
    elif "/add-card-requests" in p:
        body = acr
    elif p.endswith("/bank-details"):
        body = paged(bd) if m == "GET" else bd
    elif "/bank-details/" in p:
        body = bd
    elif p.endswith("/scoring"):
        body = paged({"status": "SUCCEEDED", "beneficiaryId": "b"})
    elif p.endswith("/beneficiaries"):
        body = paged(ben) if m == "GET" else ben
    elif p.endswith("/deponents"):
        body = paged(dep)
    elif "/deponents/" in p:
        body = dep
    elif p.endswith("/recipients"):
        body = paged(rec) if m == "GET" else rec
    elif "/recipients/" in p:
        body = rec
    elif p.endswith("/steps"):
        body = paged(step) if m == "GET" else step
    elif "/steps/" in p:
        body = step
    elif p.endswith("/is-valid"):
        body = {"isValid": True}
    elif p.endswith("/deals"):
        body = paged(deal) if m == "GET" else deal
    elif p.endswith("/payments"):
        body = paged(pay) if m == "GET" else pay
    elif "/payments/" in p:
        body = pay
    elif p.endswith("/incoming-transactions"):
        body = paged({"accountNumber": _ACC, "operationId": "op", "amount": 1})
    elif p.endswith("/balances"):
        body = paged(
            {
                "beneficiaryId": "b",
                "accountNumber": _ACC,
                "amount": 1,
                "amountOnHold": 0,
            }
        )
    elif p.endswith("/holds"):
        body = paged(
            {"beneficiaryId": "b", "accountNumber": _ACC, "holdId": "h", "amount": 1}
        )
    elif p.endswith("/transfers"):
        body = paged(transfer) if m == "GET" else transfer
    elif "/transfers/" in p:
        body = transfer
    elif "/deals/" in p:
        body = deal
    elif "/beneficiaries/" in p:
        body = ben
    else:  # pragma: no cover
        raise AssertionError(f"unrouted {m} {p}")
    return httpx.Response(200, json=body)


def test_sync_full_surface():
    """Прогоняет все 48 sync-методов — ловит расхождения с async-зеркалом."""
    client = _sync_client(_sync_surface_handler, _sync_surface_handler)
    bd_req = RkcBankDetailsRequest(
        bik="044525225",
        bank_name="Т-Банк",
        account_number=_ACC,
        corr_account_number="30101810000000000225",
    )
    assert client.list_beneficiaries().total == 1
    assert client.create_beneficiary(_fl_beneficiary()).beneficiary_id == "b"
    assert client.get_beneficiary("b").beneficiary_id == "b"
    client.update_beneficiary("b", _fl_beneficiary())
    client.create_add_card_request("b", AddCardRequest(terminal_key="TK"))
    client.get_add_card_request("b", "acr")
    client.list_bank_details("b")
    assert client.create_bank_details("b", bd_req).bank_details_id == "bd"
    client.get_bank_details("b", "bd")
    client.update_bank_details("b", "bd", bd_req)
    assert client.delete_bank_details("b", "bd") is None
    assert client.set_default_bank_details("b", "bd") is None
    assert client.get_beneficiaries_scoring().total == 1

    client.list_deals()
    assert client.create_deal(DealRequest(account_number=_ACC)).deal_id == "d"
    assert client.get_deal("d").deal_id == "d"
    assert client.delete_deal("d") is None
    assert client.accept_deal("d") is None
    assert client.cancel_deal("d") is None
    assert client.draft_deal("d") is None
    assert client.get_deal_validity("d").is_valid is True

    client.list_steps("d")
    assert client.create_step("d", StepRequest(description="x")).step_id == "s"
    client.get_step("d", "s")
    client.update_step("d", "s", StepRequest(description="x"))
    assert client.delete_step("d", "s") is None
    assert client.complete_step("d", "s") is None

    client.list_deponents("d", "s")
    client.get_deponent("d", "s", "b")
    client.set_deponent("d", "s", "b", DeponentRequest(amount=Decimal("1")))
    assert client.delete_deponent("d", "s", "b") is None

    rec_req = RecipientRequest(beneficiary_id="b", amount=Decimal("1"))
    client.list_recipients("d", "s")
    assert client.create_recipient("d", "s", rec_req).recipient_id == "r"
    client.get_recipient("d", "s", "r")
    client.update_recipient("d", "s", "r", rec_req)
    assert client.delete_recipient("d", "s", "r") is None
    assert (
        client.update_recipient_bank_details(
            "d", "s", "r", UpdateRecipientBankDetailsRequest(bank_details_id="bd")
        )
        is None
    )

    client.list_payments()
    reg = CreateRegularPaymentRequest(
        beneficiary_id="b", account_number=_ACC, amount=Decimal("1"), purpose="x"
    )
    assert client.create_payment(reg).payment_id == "p"
    assert client.get_payment("p").payment_id == "p"
    assert client.retry_payment("p").retry_payment_id == "rp"

    client.list_incoming_transactions()
    assert (
        client.identify_incoming_transaction("op", IdentifyIncomingTransactionRequest())
        is None
    )

    client.list_balances()
    client.list_holds()
    client.list_transfers(_ACC)
    transfer_req = CreateTransferRequest(
        account_number=_ACC,
        from_=TransferParty(beneficiary_id="a"),
        to=TransferParty(beneficiary_id="z"),
        amount=Decimal("1"),
    )
    assert client.create_transfer(transfer_req).transfer_id == "t"
    assert client.get_transfer("t").to.beneficiary_id == "z"
    client.close()


async def test_async_full_surface():
    """Зеркало sync smoke-теста для async-клиента — все 48 методов."""
    client = _client(_sync_surface_handler, _sync_surface_handler)
    bd_req = RkcBankDetailsRequest(
        bik="044525225",
        bank_name="Т-Банк",
        account_number=_ACC,
        corr_account_number="30101810000000000225",
    )
    assert (await client.list_beneficiaries()).total == 1
    assert (await client.create_beneficiary(_fl_beneficiary())).beneficiary_id == "b"
    assert (await client.get_beneficiary("b")).beneficiary_id == "b"
    await client.update_beneficiary("b", _fl_beneficiary())
    await client.create_add_card_request("b", AddCardRequest(terminal_key="TK"))
    await client.get_add_card_request("b", "acr")
    await client.list_bank_details("b")
    assert (await client.create_bank_details("b", bd_req)).bank_details_id == "bd"
    await client.get_bank_details("b", "bd")
    await client.update_bank_details("b", "bd", bd_req)
    assert await client.delete_bank_details("b", "bd") is None
    assert await client.set_default_bank_details("b", "bd") is None
    assert (await client.get_beneficiaries_scoring()).total == 1

    await client.list_deals()
    assert (await client.create_deal(DealRequest(account_number=_ACC))).deal_id == "d"
    assert (await client.get_deal("d")).deal_id == "d"
    assert await client.delete_deal("d") is None
    assert await client.accept_deal("d") is None
    assert await client.cancel_deal("d") is None
    assert await client.draft_deal("d") is None
    assert (await client.get_deal_validity("d")).is_valid is True

    await client.list_steps("d")
    assert (await client.create_step("d", StepRequest(description="x"))).step_id == "s"
    await client.get_step("d", "s")
    await client.update_step("d", "s", StepRequest(description="x"))
    assert await client.delete_step("d", "s") is None
    assert await client.complete_step("d", "s") is None

    await client.list_deponents("d", "s")
    await client.get_deponent("d", "s", "b")
    await client.set_deponent("d", "s", "b", DeponentRequest(amount=Decimal("1")))
    assert await client.delete_deponent("d", "s", "b") is None

    rec_req = RecipientRequest(beneficiary_id="b", amount=Decimal("1"))
    await client.list_recipients("d", "s")
    assert (await client.create_recipient("d", "s", rec_req)).recipient_id == "r"
    await client.get_recipient("d", "s", "r")
    await client.update_recipient("d", "s", "r", rec_req)
    assert await client.delete_recipient("d", "s", "r") is None
    assert (
        await client.update_recipient_bank_details(
            "d", "s", "r", UpdateRecipientBankDetailsRequest(bank_details_id="bd")
        )
        is None
    )

    await client.list_payments()
    reg = CreateRegularPaymentRequest(
        beneficiary_id="b", account_number=_ACC, amount=Decimal("1"), purpose="x"
    )
    assert (await client.create_payment(reg)).payment_id == "p"
    assert (await client.get_payment("p")).payment_id == "p"
    assert (await client.retry_payment("p")).retry_payment_id == "rp"

    await client.list_incoming_transactions()
    assert (
        await client.identify_incoming_transaction(
            "op", IdentifyIncomingTransactionRequest()
        )
        is None
    )

    await client.list_balances()
    await client.list_holds()
    await client.list_transfers(_ACC)
    transfer_req = CreateTransferRequest(
        account_number=_ACC,
        from_=TransferParty(beneficiary_id="a"),
        to=TransferParty(beneficiary_id="z"),
        amount=Decimal("1"),
    )
    assert (await client.create_transfer(transfer_req)).transfer_id == "t"
    assert (await client.get_transfer("t")).to.beneficiary_id == "z"


def test_sandbox_url_constants():
    assert SANDBOX_URL == "https://business.tbank.ru/openapi/sandbox"
    assert PROD_URL == "https://business.tbank.ru/openapi"
