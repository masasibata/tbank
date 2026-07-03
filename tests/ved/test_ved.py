import base64
import hashlib
import hmac
import json

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, MutualTLSRequiredError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.ved.aio import PROD_URL, SECURED_URL, VedClient
from tbank.ved.enums import ApplicationStatus, ContractSubject, ContractType
from tbank.ved.errors import CurrencySignatureRequiredError
from tbank.ved.models import (
    AmendContractRequest,
    ContractInfo,
    DeregisterContractRequest,
    RegisterContractRequest,
)
from tbank.ved.signing import CurrencySignature
from tbank.ved.sync import VedClient as SyncClient

_SIG = CurrencySignature("key-1", "topsecret")


def _transport(handler, base_url, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=base_url, client=client, auth=BearerAuth("T"))


def _client(reg=None, sec=None, *, signature=_SIG):
    return VedClient(
        token="T",
        signature=signature,
        transport=_transport(reg or (lambda r: httpx.Response(500)), PROD_URL),
        secured_transport=_transport(sec, SECURED_URL) if sec else None,
    )


def _registration():
    return RegisterContractRequest(
        open_api_application_id="app-1",
        contract_info=ContractInfo(
            contract_subject=ContractSubject.GOODS,
            contract_type=ContractType.EXPORT,
            currency_code="840",
            contract_date="2026-01-10",
            exchange_rate_effective_date="2026-01-10",
        ),
    )


# --- Подпись ---


def test_signing_string_and_data():
    body = b'{"a":1}'
    sig = CurrencySignature("kid", "sec")
    headers = sig.build_headers("POST", "/api/v1/x", body, date="2026-01-01T00:00:00Z")
    expected_data = base64.b64encode(
        hmac.new(b"sec", body, hashlib.sha256).digest()
    ).decode()
    assert headers["data"] == expected_data
    signing_string = (
        "(request-target): post /api/v1/x?\n"
        "date: 2026-01-01T00:00:00Z\n"
        f"data: {expected_data}"
    )
    expected_sig = base64.b64encode(
        hmac.new(b"sec", signing_string.encode(), hashlib.sha256).digest()
    ).decode()
    assert f'signature="{expected_sig}"' in headers["Signature"]
    assert 'keyId="kid"' in headers["Signature"]
    assert 'algorithm="HMAC-SHA256"' in headers["Signature"]


# --- Подписанные методы (mTLS) ---


async def test_register_contract_signed():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        assert request.url.path == "/api/v1/currency/contracts/openapi/registration"
        assert request.headers["content-type"] == "application/json"
        assert request.headers.get("Signature", "").startswith("Signature keyId=")
        # data-заголовок должен быть HMAC над реально отправленным телом
        expected = base64.b64encode(
            hmac.new(b"topsecret", request.content, hashlib.sha256).digest()
        ).decode()
        assert request.headers["data"] == expected
        body = json.loads(request.content)
        assert body["contractInfo"]["contractSubject"] == 0  # IntEnum → int
        assert body["contractInfo"]["contractType"] == 0
        return httpx.Response(200, json={"openApiApplicationId": "app-1"})

    client = _client(sec=sec)
    result = await client.register_contract(_registration())
    assert result.open_api_application_id == "app-1"


async def test_amend_and_deregister():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Signature")
        return httpx.Response(200, json={"openApiApplicationId": "app-2"})

    client = _client(sec=sec)
    amended = await client.amend_contract(
        AmendContractRequest(
            open_api_application_id="app-2",
            unique_contract_number="UCN-1",
            amendments={"note": "смена суммы"},
        )
    )
    assert amended.open_api_application_id == "app-2"
    dereg = await client.deregister_contract(
        DeregisterContractRequest(
            open_api_application_id="app-2",
            unique_contract_number="UCN-1",
            deregistration_reason=3,
        )
    )
    assert dereg.open_api_application_id == "app-2"


async def test_signature_required_without_creds():
    client = _client(sec=lambda r: httpx.Response(200, json={}), signature=None)
    with pytest.raises(CurrencySignatureRequiredError):
        await client.register_contract(_registration())


async def test_signed_without_cert_raises():
    client = _client()  # signature есть, secured_transport нет
    with pytest.raises(MutualTLSRequiredError):
        await client.register_contract(_registration())


# --- Статус (обычный хост) ---


async def test_get_application_status():
    def reg(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        assert request.url.path == (
            "/openapi/api/v2/currency/contracts/applications/openapi/status"
        )
        assert request.url.params.get("openApiApplicationId") == "app-1"
        return httpx.Response(
            200,
            json={
                "openApiApplicationId": "app-1",
                "status": "APPROVED",
                "datetime": "2026-01-11T10:00:00+03:00",
                "metadata": {"uniqueContractNumber": "UCN-1"},
            },
        )

    status = await _client(reg=reg).get_application_status("app-1")
    assert status.status == ApplicationStatus.APPROVED
    assert status.metadata.unique_contract_number == "UCN-1"


async def test_error_mapping():
    client = _client(
        reg=lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        await client.get_application_status("app-1")
    assert exc.value.error_id == "e"


# --- Синхронный клиент ---


def test_sync_client():
    def sec(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Signature")
        return httpx.Response(200, json={"openApiApplicationId": "app-9"})

    def reg(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = SyncClient(
        token="T",
        signature=_SIG,
        transport=_transport(reg, PROD_URL, sync=True),
        secured_transport=_transport(sec, SECURED_URL, sync=True),
    )
    assert client.register_contract(_registration()).open_api_application_id == "app-9"
    assert (
        client.amend_contract(
            AmendContractRequest(
                open_api_application_id="a",
                unique_contract_number="U",
                amendments={"x": 1},
            )
        ).open_api_application_id
        == "app-9"
    )
    assert (
        client.deregister_contract(
            DeregisterContractRequest(
                open_api_application_id="a",
                unique_contract_number="U",
                deregistration_reason=0,
            )
        ).open_api_application_id
        == "app-9"
    )
    with pytest.raises(TBankAPIError):
        client.get_application_status("app-1")
    client.close()


def test_sync_status_success_and_signature_required():
    def reg(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "openApiApplicationId": "app-1",
                "status": "SUBMITTED",
                "datetime": "2026-01-11T10:00:00+03:00",
                "metadata": {},
            },
        )

    client = SyncClient(token="T", transport=_transport(reg, PROD_URL, sync=True))
    assert client.get_application_status("app-1").status == ApplicationStatus.SUBMITTED
    with pytest.raises(CurrencySignatureRequiredError):
        client.register_contract(_registration())
    client.close()
