import json
from datetime import date, datetime

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, ValidationError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.tid.aio import TidClient as AsyncTidClient
from tbank.tid.enums import (
    BundleCode,
    CardType,
    Grade,
    IdDocumentType,
    IdentificationResult,
    LegalStatus,
    TaxationScheme,
)
from tbank.tid.models import SetCounterRequest
from tbank.tid.sync import TidClient as SyncTidClient


def _async_client(handler):
    transport = AsyncTransport(
        base_url="https://business.tbank.ru/openapi",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        auth=BearerAuth("TKN"),
    )
    return AsyncTidClient(token="TKN", transport=transport)


def _sync_client(handler):
    transport = SyncTransport(
        base_url="https://business.tbank.ru/openapi",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        auth=BearerAuth("TKN"),
    )
    return SyncTidClient(token="TKN", transport=transport)


COMPANY_BODY = {
    "name": "ООО Ромашка",
    "city": "Москва",
    "requisites": {
        "fullName": "Общество Ромашка",
        "address": "г. Москва",
        "legalAddress": "г. Москва, ул. Ленина",
        "inn": "7700000000",
        "kpp": "770001001",
        "ogrn": "1157700000000",
    },
    "bank": {
        "bankName": "Т-Банк",
        "bankAddress": "Москва",
        "corrAccount": "30101810145250000974",
        "bankInn": "7710140679",
        "bankBic": "044525974",
    },
    "registrationDate": "2015-05-01",
    "opf": "ООО",
    "taxationScheme": "USN_INCOMES",
    "legalStatus": "active",
}


async def test_get_company_parses_enums_date_and_nested():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer TKN"
        assert request.url.path == "/openapi/api/v2/company"
        return httpx.Response(200, json=COMPANY_BODY)

    client = _async_client(handler)
    company = await client.get_company()
    assert company.name == "ООО Ромашка"
    assert company.taxation_scheme is TaxationScheme.USN_INCOMES
    assert company.legal_status is LegalStatus.ACTIVE
    assert company.registration_date == date(2015, 5, 1)
    assert company.requisites.inn == "7700000000"
    assert company.bank.bank_bic == "044525974"
    await client.aclose()


async def test_signer_status_and_flag_statuses():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        mapping = {
            "/openapi/api/v2/company/signer/status": {"isSigner": True},
            "/openapi/api/v2/individual/identification/status": {"isIdentified": True},
            "/openapi/api/v2/individual/self-employed/status": {
                "isSelfEmployed": False
            },
            "/openapi/api/v2/individual/foreignagent/status": {"isForeignAgent": False},
            "/openapi/api/v2/individual/pdl/status": {"isPublicOfficialPerson": True},
            "/openapi/api/v2/individual/blacklist/status": {"isBlacklisted": False},
        }
        return httpx.Response(200, json=mapping[path])

    client = _async_client(handler)
    assert (await client.get_signer_status()).is_signer is True
    assert (await client.get_identification_status()).is_identified is True
    assert (await client.get_self_employed_status()).is_self_employed is False
    assert (await client.get_foreign_agent_status()).is_foreign_agent is False
    assert (await client.get_pdl_status()).is_public_official_person is True
    assert (await client.get_blacklist_status()).is_blacklisted is False
    await client.aclose()


async def test_userinfo_documents_and_accounts():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/individual/userinfo"):
            return httpx.Response(
                200,
                json={
                    "sub": "11111111-1111-1111-1111-111111111111",
                    "phoneNumber": "+70000000000",
                    "givenName": "Иван",
                    "familyName": "Петров",
                    "birthDate": "1990-01-02",
                },
            )
        if path.endswith("/documents/inn"):
            return httpx.Response(200, json={"inn": "770012345678"})
        if path.endswith("/documents/snils"):
            return httpx.Response(200, json={"snils": "112-233-445 95"})
        if path.endswith("/documents/driver-licenses"):
            return httpx.Response(
                200,
                json={
                    "licenses": [{"docNumber": "7700111222", "issueDate": "2020-06-01"}]
                },
            )
        if path.endswith("/accounts/debit"):
            return httpx.Response(
                200,
                json={
                    "accounts": [
                        {
                            "name": "Основной",
                            "accountNumber": "40817810000000000001",
                            "bank": {
                                "bik": "044525974",
                                "corAccount": "30101810145250000974",
                                "name": "Т-Банк",
                            },
                        }
                    ]
                },
            )
        raise AssertionError(path)

    client = _async_client(handler)
    info = await client.get_userinfo()
    assert info.given_name == "Иван" and info.birth_date == date(1990, 1, 2)
    assert (await client.get_inn()).inn == "770012345678"
    assert (await client.get_snils()).snils == "112-233-445 95"
    lic = await client.get_driver_licenses()
    assert lic.licenses[0].doc_number == "7700111222"
    assert lic.licenses[0].issue_date == date(2020, 6, 1)
    accs = await client.get_debit_accounts()
    assert accs.accounts[0].bank.bik == "044525974"
    await client.aclose()


async def test_passport_sends_idtype_array_query():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["idType"] = request.url.params.get_list("idType")
        return httpx.Response(
            200,
            json={
                "serialNumber": "4500 123456",
                "issueDate": "2010-03-04",
                "numberOfChildren": 2,
                "resident": True,
                "idType": "PASSPORT",
            },
        )

    client = _async_client(handler)
    passport = await client.get_passport(
        [IdDocumentType.PASSPORT, IdDocumentType.FOREIGN_PASSPORT]
    )
    assert seen["path"] == "/openapi/api/v2/individual/documents/passport"
    assert seen["idType"] == ["PASSPORT", "FOREIGN_PASSPORT"]
    assert passport.number_of_children == 2
    assert passport.id_type is IdDocumentType.PASSPORT
    assert passport.issue_date == date(2010, 3, 4)
    await client.aclose()


async def test_addresses_sends_addresstype_query():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["addressType"] = request.url.params.get("addressType")
        return httpx.Response(
            200,
            json={
                "addresses": [
                    {
                        "addressType": "REGISTRATION_ADDRESS",
                        "primary": True,
                        "city": "Москва",
                        "latitude": 55.75,
                        "longitude": 37.61,
                    }
                ]
            },
        )

    client = _async_client(handler)
    resp = await client.get_addresses("REGISTRATION_ADDRESS")
    assert seen["addressType"] == "REGISTRATION_ADDRESS"
    assert resp.addresses[0].primary is True
    assert resp.addresses[0].latitude == 55.75
    await client.aclose()


async def test_cobrand_path_param_and_card_type():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openapi/api/v1/individual/cobrand/42"
        return httpx.Response(
            200,
            json={
                "programStatus": True,
                "accounts": [{"cardType": "DEBIT", "loyaltyId": "L-1"}],
            },
        )

    client = _async_client(handler)
    resp = await client.get_cobrand(42)
    assert resp.program_status is True
    assert resp.accounts[0].card_type is CardType.DEBIT
    await client.aclose()


async def test_detail_counters_get_and_post():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = json.loads(request.content)
            assert body["count"] == 5
            assert body["extraFields"]["description"] == "бонус"
            assert body["requestId"] == "req-1"
            return httpx.Response(200, json={"count": 5, "isInfinity": False})
        return httpx.Response(
            200,
            json={
                "clientInfo": {"grade": "SECOND", "isFulfillConditions": True},
                "counterInfo": {
                    "count": 3,
                    "isInfinity": False,
                    "period": {
                        "validFrom": "2026-01-01",
                        "validUntil": "2026-12-31",
                        "repeatability": "YEAR",
                    },
                },
            },
        )

    client = _async_client(handler)
    counters = await client.get_detail_counters()
    assert counters.client_info.grade is Grade.SECOND
    assert counters.counter_info.period.repeatability.value == "YEAR"
    updated = await client.set_detail_counters(
        SetCounterRequest(
            count=5,
            extra_fields={"description": "бонус"},
            request_id="req-1",
        )
    )
    assert updated.count == 5 and updated.is_infinity is False
    await client.aclose()


async def test_subscriptions():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/subscription/grade"):
            return httpx.Response(200, json={"bundleCode": "PRO", "gradeCode": "G2"})
        return httpx.Response(200, json={"type": "PREMIUM"})

    client = _async_client(handler)
    sub = await client.get_subscription()
    assert sub.type is BundleCode.PREMIUM
    grade = await client.get_subscription_grade()
    assert grade.bundle_code == "PRO" and grade.grade_code == "G2"
    await client.aclose()


async def test_delegated_identification():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/individual/delegated-identification")
        return httpx.Response(
            200,
            json={
                "dateTimeDelegatedIdentified": "2026-07-01T10:00:00Z",
                "sub": "s-1",
                "phoneNumber": "+70000000000",
                "familyName": "Петров",
                "givenName": "Иван",
                "passportBirthDate": "1990-01-02",
                "issueDate": "2010-03-04",
                "serialNumber": "4500 123456",
                "unitCode": "770-001",
                "unitName": "ОВД",
                "idType": "PASSPORT",
                "addressType": "REGISTRATION_ADDRESS",
                "isForeignAgent": False,
                "isBlacklisted": False,
            },
        )

    client = _async_client(handler)
    di = await client.get_delegated_identification()
    assert di.sub == "s-1"
    assert di.date_time_delegated_identified == datetime(
        2026, 7, 1, 10, 0, tzinfo=di.date_time_delegated_identified.tzinfo
    )
    assert di.passport_birth_date == date(1990, 1, 2)
    assert di.is_foreign_agent is False
    await client.aclose()


IDENT_BODY = {
    "result": "SUCCESS",
    "personalInfo": {
        "firstName": "Иван",
        "lastName": "Петров",
        "birthDate": "1990-01-02",
        "address": {"addressType": "REGISTRATION_ADDRESS", "city": "Москва"},
        "document": [
            {
                "documentType": "PASSPORT",
                "serNo": "4500 123456",
                "issueDate": "2010-03-04",
                "documentCheckStatus": "VALID",
            }
        ],
        "inn": "770012345678",
        "sub": "s-1",
    },
}


async def test_personal_data_and_remote_identification():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = json.loads(request.content)
            assert body == {"resSecret": "secret-xyz"}
            assert request.url.path.endswith("/bio/remote-identification/result")
            return httpx.Response(200, json=IDENT_BODY)
        assert request.url.path == (
            "/openapi/api/v1/identification/personalData/req-uuid"
        )
        return httpx.Response(200, json=IDENT_BODY)

    client = _async_client(handler)
    by_id = await client.get_personal_data("req-uuid")
    assert by_id.result is IdentificationResult.SUCCESS
    assert by_id.personal_info is not None
    assert by_id.personal_info.document[0].ser_no == "4500 123456"
    remote = await client.get_remote_identification_result("secret-xyz")
    assert remote.personal_info is not None
    assert remote.personal_info.address is not None
    assert remote.personal_info.address.city == "Москва"
    await client.aclose()


async def test_error_mapping_forbidden_and_validation():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/pdl/status"):
            return httpx.Response(
                403,
                json={
                    "errorId": "e-1",
                    "errorCode": "INSUFFICIENT_SCOPE",
                    "errorMessage": "нет скоупа",
                    "errorDetails": "opensme/individual/pdl/status/get",
                },
            )
        return httpx.Response(400, json={"errorMessage": "bad"})

    client = _async_client(handler)
    with pytest.raises(ForbiddenError) as exc:
        await client.get_pdl_status()
    assert exc.value.error_id == "e-1"
    assert exc.value.code == "INSUFFICIENT_SCOPE"
    assert exc.value.http_status == 403
    with pytest.raises(ValidationError):
        await client.get_blacklist_status()
    await client.aclose()


async def test_non_json_error_body_falls_back_to_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    client = _async_client(handler)
    with pytest.raises(ForbiddenError) as exc:
        await client.get_inn()
    assert exc.value.code == "403"
    assert exc.value.message == "forbidden"
    assert exc.value.error_id is None
    await client.aclose()


def test_sync_error_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"errorMessage": "bad request"})

    client = _sync_client(handler)
    with pytest.raises(ValidationError):
        client.get_snils()
    client.close()


def test_sync_client_covers_all_paths():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/v2/company"):
            return httpx.Response(200, json=COMPANY_BODY)
        if path.endswith("/company/signer/status"):
            return httpx.Response(200, json={"isSigner": False})
        if path.endswith("/individual/userinfo"):
            return httpx.Response(200, json={"sub": "s"})
        if path.endswith("/documents/inn"):
            return httpx.Response(200, json={"inn": "1"})
        if path.endswith("/documents/snils"):
            return httpx.Response(200, json={"snils": "2"})
        if path.endswith("/documents/passport"):
            return httpx.Response(200, json={"serialNumber": "3"})
        if path.endswith("/documents/driver-licenses"):
            return httpx.Response(200, json={"licenses": []})
        if path.endswith("/individual/addresses"):
            return httpx.Response(200, json={"addresses": []})
        if path.endswith("/accounts/debit"):
            return httpx.Response(200, json={"accounts": []})
        if path.endswith("/identification/status"):
            return httpx.Response(200, json={"isIdentified": True})
        if path.endswith("/self-employed/status"):
            return httpx.Response(200, json={"isSelfEmployed": True})
        if path.endswith("/foreignagent/status"):
            return httpx.Response(200, json={"isForeignAgent": True})
        if path.endswith("/pdl/status"):
            return httpx.Response(200, json={"isPublicOfficialPerson": True})
        if path.endswith("/blacklist/status"):
            return httpx.Response(200, json={"isBlacklisted": True})
        if "/cobrand/" in path:
            return httpx.Response(200, json={"programStatus": False})
        if path.endswith("/detail-counters") and request.method == "POST":
            return httpx.Response(200, json={"count": 1, "isInfinity": True})
        if path.endswith("/detail-counters"):
            return httpx.Response(
                200,
                json={
                    "clientInfo": {"grade": "NONE", "isFulfillConditions": False},
                    "counterInfo": {
                        "count": 0,
                        "isInfinity": True,
                        "period": {
                            "validFrom": "a",
                            "validUntil": "b",
                            "repeatability": "MONTH",
                        },
                    },
                },
            )
        if path.endswith("/subscription/grade"):
            return httpx.Response(200, json={})
        if path.endswith("/subscription"):
            return httpx.Response(200, json={"type": "DEFAULT"})
        if path.endswith("/delegated-identification"):
            return httpx.Response(
                200,
                json={
                    "dateTimeDelegatedIdentified": "2026-07-01T10:00:00Z",
                    "sub": "s",
                    "phoneNumber": "p",
                    "familyName": "f",
                    "givenName": "g",
                    "passportBirthDate": "1990-01-02",
                    "issueDate": "2010-03-04",
                    "serialNumber": "n",
                    "unitCode": "u",
                    "unitName": "un",
                    "idType": "PASSPORT",
                    "addressType": "RESIDENCE_ADDRESS",
                },
            )
        if "/personalData/" in path:
            return httpx.Response(200, json=IDENT_BODY)
        if path.endswith("/bio/remote-identification/result"):
            return httpx.Response(200, json={"result": "FAILED"})
        raise AssertionError(path)

    c = _sync_client(handler)
    assert c.get_company().city == "Москва"
    assert c.get_signer_status().is_signer is False
    assert c.get_userinfo().sub == "s"
    assert c.get_inn().inn == "1"
    assert c.get_snils().snils == "2"
    assert c.get_passport().serial_number == "3"
    assert c.get_passport([IdDocumentType.PASSPORT]).serial_number == "3"
    assert c.get_driver_licenses().licenses == []
    assert c.get_addresses().addresses == []
    assert c.get_addresses("WORK_ADDRESS").addresses == []
    assert c.get_debit_accounts().accounts == []
    assert c.get_identification_status().is_identified is True
    assert c.get_self_employed_status().is_self_employed is True
    assert c.get_foreign_agent_status().is_foreign_agent is True
    assert c.get_pdl_status().is_public_official_person is True
    assert c.get_blacklist_status().is_blacklisted is True
    assert c.get_cobrand(7).program_status is False
    assert c.get_detail_counters().counter_info.is_infinity is True
    assert c.set_detail_counters(SetCounterRequest(count=1)).is_infinity is True
    assert c.get_subscription().type is BundleCode.DEFAULT
    assert c.get_subscription_grade().bundle_code is None
    assert c.get_delegated_identification().sub == "s"
    assert c.get_personal_data("x").result is IdentificationResult.SUCCESS
    assert c.get_remote_identification_result("s").result is IdentificationResult.FAILED
    c.close()
