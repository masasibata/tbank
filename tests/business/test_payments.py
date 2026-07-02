import json
from decimal import Decimal

import httpx
import pytest

from tbank.business.aio import BusinessClient as AsyncBusinessClient
from tbank.business.enums import PaymentStatus
from tbank.business.models import (
    CreatePaymentRequest,
    PaymentFrom,
    ReceiverRequisites,
    TaxPaymentParameters,
    ThirdParty,
)
from tbank.business.sync import BusinessClient as SyncBusinessClient
from tbank.core.auth import BearerAuth
from tbank.core.errors import MutualTLSRequiredError
from tbank.core.transport import AsyncTransport, SyncTransport


def _default_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={})


def _async_client(normal_handler=None, secured_handler=None):
    normal = AsyncTransport(
        base_url="https://business.tbank.ru/openapi",
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(normal_handler or _default_handler)
        ),
        auth=BearerAuth("TKN"),
    )
    secured = None
    if secured_handler is not None:
        secured = AsyncTransport(
            base_url="https://secured-openapi.tbank.ru",
            client=httpx.AsyncClient(transport=httpx.MockTransport(secured_handler)),
            auth=BearerAuth("TKN"),
        )
    return AsyncBusinessClient(token="TKN", transport=normal, secured_transport=secured)


def _payment(**over) -> CreatePaymentRequest:
    kwargs = dict(
        from_=PaymentFrom(account_number="40802"),
        to=ReceiverRequisites(
            name="ООО Ромашка",
            inn="7700000000",
            account_number="40702",
            bik="044525974",
        ),
        purpose="Оплата по счёту 1",
        amount=Decimal("12345.67"),
    )
    kwargs.update(over)
    return CreatePaymentRequest(**kwargs)


async def test_create_ruble_payment_routes_to_secured_and_sends_number_amount():
    seen = {}

    def secured_handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.url.host
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(201)

    client = _async_client(secured_handler=secured_handler)
    result = await client.create_ruble_payment(_payment(id="pay-1"))
    assert result == "pay-1"
    assert seen["host"] == "secured-openapi.tbank.ru"
    assert seen["path"] == "/api/v1/payment/ruble-transfer/pay"
    assert seen["auth"] == "Bearer TKN"
    assert seen["body"]["amount"] == 12345.67  # число, не строка
    assert isinstance(seen["body"]["amount"], float)
    assert seen["body"]["from"]["accountNumber"] == "40802"
    assert seen["body"]["to"]["inn"] == "7700000000"
    assert seen["body"]["id"] == "pay-1"
    await client.aclose()


async def test_create_payment_autogenerates_id():
    def secured_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201)

    client = _async_client(secured_handler=secured_handler)
    pid = await client.create_ruble_payment(_payment())
    assert isinstance(pid, str) and len(pid) >= 8
    await client.aclose()


async def test_create_tax_payment_includes_tax_block():
    seen = {}

    def secured_handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(201)

    client = _async_client(secured_handler=secured_handler)
    tax = TaxPaymentParameters(
        payer_status="01",
        kbk="18210101011011000110",
        oktmo="45000000",
        evidence="ТП",
        period="01.01.2026",
        doc_number="0",
        doc_date="01.01.2026",
        third_party=ThirdParty(inn="7700000000", kpp="770001001"),
    )
    await client.create_ruble_payment(_payment(tax=tax))
    assert seen["body"]["tax"]["kbk"] == "18210101011011000110"
    assert seen["body"]["tax"]["period"] == "01.01.2026"
    assert seen["body"]["tax"]["thirdParty"]["inn"] == "7700000000"
    await client.aclose()


async def test_get_payment_status_secured():
    def secured_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/payment/pay-1"
        return httpx.Response(200, json={"status": "EXECUTED"})

    client = _async_client(secured_handler=secured_handler)
    status = await client.get_payment_status("pay-1")
    assert status.status is PaymentStatus.EXECUTED
    await client.aclose()


async def test_get_documents_status_uses_normal_host():
    seen = {}

    def normal_handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "result": [{"documentId": "d1", "status": "EXECUTED"}],
                "resultError": [],
            },
        )

    client = _async_client(normal_handler=normal_handler)
    resp = await client.get_documents_status(["d1", "d2"])
    assert seen["path"] == "/openapi/api/v1/payment/status"
    assert seen["body"]["documentIds"] == ["d1", "d2"]
    assert resp.result[0].document_id == "d1"
    await client.aclose()


async def test_secured_method_without_cert_raises():
    client = _async_client()  # нет secured-транспорта
    with pytest.raises(MutualTLSRequiredError):
        await client.get_payment_status("pay-1")
    with pytest.raises(MutualTLSRequiredError):
        await client.create_ruble_payment(_payment())
    await client.aclose()


def test_sync_create_ruble_payment():
    def secured_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201)

    secured = SyncTransport(
        base_url="https://secured-openapi.tbank.ru",
        client=httpx.Client(transport=httpx.MockTransport(secured_handler)),
        auth=BearerAuth("TKN"),
    )
    normal = SyncTransport(
        base_url="https://business.tbank.ru/openapi",
        client=httpx.Client(transport=httpx.MockTransport(_default_handler)),
        auth=BearerAuth("TKN"),
    )
    client = SyncBusinessClient(
        token="TKN", transport=normal, secured_transport=secured
    )
    assert client.create_ruble_payment(_payment(id="s-1")) == "s-1"
    client.close()


def test_sync_payment_status_and_documents_status():
    def secured_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "IN_PROGRESS"})

    def normal_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": [], "resultError": []})

    secured = SyncTransport(
        base_url="https://secured-openapi.tbank.ru",
        client=httpx.Client(transport=httpx.MockTransport(secured_handler)),
        auth=BearerAuth("TKN"),
    )
    normal = SyncTransport(
        base_url="https://business.tbank.ru/openapi",
        client=httpx.Client(transport=httpx.MockTransport(normal_handler)),
        auth=BearerAuth("TKN"),
    )
    client = SyncBusinessClient(
        token="TKN", transport=normal, secured_transport=secured
    )
    assert client.get_payment_status("p1").status is PaymentStatus.IN_PROGRESS
    assert client.get_documents_status(["d1"]).result == []
    client.close()
