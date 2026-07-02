from __future__ import annotations

from typing import Any, List, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.endpoint import Endpoint
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.tid.enums import IdDocumentType, TokenTypeHint
from tbank.tid.errors import error_from_tid_response
from tbank.tid.models import (
    AddressesResponse,
    BlacklistStatus,
    CobrandResponse,
    CompanyInfo,
    DebitAccountsResponse,
    DelegatedIdentification,
    DetailCounters,
    DriverLicensesResponse,
    ForeignAgentStatus,
    IdentificationData,
    IdentificationStatus,
    InnResponse,
    IntrospectionResponse,
    OidcUserInfo,
    PassportData,
    PdlStatus,
    RemoteIdentificationRequest,
    SelfEmployedStatus,
    SetCounterRequest,
    SetCounterResponse,
    SignerStatus,
    SnilsResponse,
    SubscriptionGrade,
    SubscriptionResponse,
    TokenResponse,
    UserAccountInfo,
)
from tbank.tid.oauth import (
    INTROSPECT_ENDPOINT,
    REVOKE_ENDPOINT,
    TOKEN_ENDPOINT,
    USERINFO_ENDPOINT,
    Scope,
    _OAuthBase,
)

PROD_URL = "https://business.tbank.ru/openapi"

_M = TypeVar("_M", bound=BaseModel)

# Data-эндпоинты берём в максимальной доступной версии (v2 там, где она есть).
_COMPANY = Endpoint("GET", "/api/v2/company", CompanyInfo)
_SIGNER = Endpoint("GET", "/api/v2/company/signer/status", SignerStatus)
_USERINFO = Endpoint("GET", "/api/v1/individual/userinfo", UserAccountInfo)
_INN = Endpoint("GET", "/api/v2/individual/documents/inn", InnResponse)
_SNILS = Endpoint("GET", "/api/v2/individual/documents/snils", SnilsResponse)
_DRIVER_LICENSES = Endpoint(
    "GET", "/api/v2/individual/documents/driver-licenses", DriverLicensesResponse
)
_DEBIT_ACCOUNTS = Endpoint(
    "GET", "/api/v2/individual/accounts/debit", DebitAccountsResponse
)
_IDENTIFICATION_STATUS = Endpoint(
    "GET", "/api/v2/individual/identification/status", IdentificationStatus
)
_SELF_EMPLOYED = Endpoint(
    "GET", "/api/v2/individual/self-employed/status", SelfEmployedStatus
)
_FOREIGN_AGENT = Endpoint(
    "GET", "/api/v2/individual/foreignagent/status", ForeignAgentStatus
)
_PDL = Endpoint("GET", "/api/v2/individual/pdl/status", PdlStatus)
_BLACKLIST = Endpoint("GET", "/api/v2/individual/blacklist/status", BlacklistStatus)
_DETAIL_COUNTERS = Endpoint("GET", "/api/v1/individual/detail-counters", DetailCounters)
_SET_COUNTERS = Endpoint(
    "POST", "/api/v1/individual/detail-counters", SetCounterResponse, SetCounterRequest
)
_SUBSCRIPTION = Endpoint("GET", "/api/v1/individual/subscription", SubscriptionResponse)
_SUBSCRIPTION_GRADE = Endpoint(
    "GET", "/api/v1/individual/subscription/grade", SubscriptionGrade
)
_DELEGATED = Endpoint(
    "GET", "/api/v1/individual/delegated-identification", DelegatedIdentification
)
_REMOTE_ID = Endpoint(
    "POST",
    "/api/v1/bio/remote-identification/result",
    IdentificationData,
    RemoteIdentificationRequest,
)


class TidClient(BaseSyncClient):
    """Синхронный клиент data-эндпоинтов T-ID (business.tbank.ru/openapi).

    Аутентификация — Bearer self-service токен со скоупами ``opensme/...``
    (опционально mTLS-сертификат передаётся в ``cert``). Для OAuth-потока входа
    используйте :class:`TidOAuth`.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        cert: Optional[Any] = None,
        verify: Any = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[SyncTransport] = None,
    ) -> None:
        transport = transport or SyncTransport(
            base_url=base_url or PROD_URL,
            auth=BearerAuth(token),
            retry=retry,
            cert=cert,
            verify=verify,
        )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_tid_response(response)

    def _get(self, path: str, model: Type[_M], params: Any = None) -> _M:
        response = self._transport.request("GET", path, params=params)
        self._raise_for_http(response)
        return model.model_validate(self._parse_body(response))

    # --- Компания (T-Business ID) ---

    def get_company(self) -> CompanyInfo:
        """Информация о компании: реквизиты, банк, статус."""
        return self._call(_COMPANY)

    def get_signer_status(self) -> SignerStatus:
        """Является ли пользователь подписантом компании."""
        return self._call(_SIGNER)

    # --- Учётные данные и документы ---

    def get_userinfo(self) -> UserAccountInfo:
        """Учётные данные пользователя (ФИО, телефон, пол, дата рождения)."""
        return self._call(_USERINFO)

    def get_inn(self) -> InnResponse:
        """ИНН физлица."""
        return self._call(_INN)

    def get_snils(self) -> SnilsResponse:
        """СНИЛС физлица."""
        return self._call(_SNILS)

    def get_passport(
        self, id_type: Optional[List[IdDocumentType]] = None
    ) -> PassportData:
        """Паспортные данные (опционально фильтр по типам документа)."""
        params = {"idType": [t.value for t in id_type]} if id_type else None
        return self._get("/api/v2/individual/documents/passport", PassportData, params)

    def get_driver_licenses(self) -> DriverLicensesResponse:
        """Водительские удостоверения."""
        return self._call(_DRIVER_LICENSES)

    def get_addresses(self, address_type: Optional[str] = None) -> AddressesResponse:
        """Адреса физлица (опционально фильтр по типу адреса)."""
        params = {"addressType": address_type} if address_type else None
        return self._get("/api/v2/individual/addresses", AddressesResponse, params)

    def get_debit_accounts(self) -> DebitAccountsResponse:
        """Активные дебетовые счета клиента."""
        return self._call(_DEBIT_ACCOUNTS)

    # --- Статусы ---

    def get_identification_status(self) -> IdentificationStatus:
        """Идентифицирован ли пользователь."""
        return self._call(_IDENTIFICATION_STATUS)

    def get_self_employed_status(self) -> SelfEmployedStatus:
        """Статус самозанятого."""
        return self._call(_SELF_EMPLOYED)

    def get_foreign_agent_status(self) -> ForeignAgentStatus:
        """Признак иностранного агента."""
        return self._call(_FOREIGN_AGENT)

    def get_pdl_status(self) -> PdlStatus:
        """Признак публичного должностного лица."""
        return self._call(_PDL)

    def get_blacklist_status(self) -> BlacklistStatus:
        """Наличие в чёрных списках."""
        return self._call(_BLACKLIST)

    # --- Кобренд, счётчики, подписки ---

    def get_cobrand(self, program_id: int) -> CobrandResponse:
        """Признак кобренда по идентификатору программы."""
        return self._get(f"/api/v1/individual/cobrand/{program_id}", CobrandResponse)

    def get_detail_counters(self) -> DetailCounters:
        """Значение счётчика услуги клиента."""
        return self._call(_DETAIL_COUNTERS)

    def set_detail_counters(self, request: SetCounterRequest) -> SetCounterResponse:
        """Изменить значение счётчика услуги клиента."""
        return self._call(_SET_COUNTERS, request)

    def get_subscription(self) -> SubscriptionResponse:
        """Активная подписка клиента."""
        return self._call(_SUBSCRIPTION)

    def get_subscription_grade(self) -> SubscriptionGrade:
        """Код активной главной подписки и грейд клиента."""
        return self._call(_SUBSCRIPTION_GRADE)

    # --- Делегированная идентификация ---

    def get_delegated_identification(self) -> DelegatedIdentification:
        """Провести делегированную идентификацию (паспорт, адрес, флаги)."""
        return self._call(_DELEGATED)

    def get_personal_data(self, request_id: str) -> IdentificationData:
        """Результат удалённой идентификации в app-сценарии по requestId."""
        return self._get(
            f"/api/v1/identification/personalData/{request_id}", IdentificationData
        )

    def get_remote_identification_result(self, res_secret: str) -> IdentificationData:
        """Результат удалённой идентификации в web-сценарии по resSecret."""
        return self._call(
            _REMOTE_ID, RemoteIdentificationRequest(res_secret=res_secret)
        )


class TidOAuth(_OAuthBase):
    """Синхронный OAuth 2.0 / OIDC клиент T-ID (id.tbank.ru): вход и токены."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        client: Optional[httpx.Client] = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(client_id, client_secret)
        self._client = client or httpx.Client(timeout=timeout)

    def fetch_token(
        self, code: str, redirect_uri: str, *, code_verifier: Optional[str] = None
    ) -> TokenResponse:
        """Обменять authorization code на access/refresh токены."""
        response = self._client.post(
            TOKEN_ENDPOINT,
            data=self._code_form(code, redirect_uri, code_verifier),
            auth=self._basic,
        )
        return self._parse_token(response)

    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Обновить access-токен по refresh-токену."""
        response = self._client.post(
            TOKEN_ENDPOINT, data=self._refresh_form(refresh_token), auth=self._basic
        )
        return self._parse_token(response)

    def fetch_client_credentials_token(
        self, scope: Optional[Scope] = None
    ) -> TokenResponse:
        """Получить токен по client_credentials (сервис-сервис)."""
        response = self._client.post(
            TOKEN_ENDPOINT,
            data=self._client_credentials_form(scope),
            auth=self._basic,
        )
        return self._parse_token(response)

    def introspect(self, token: str) -> IntrospectionResponse:
        """Проверить токен и получить его скоупы/claim'ы (RFC 7662)."""
        response = self._client.post(
            INTROSPECT_ENDPOINT, data={"token": token}, auth=self._basic
        )
        return self._parse_introspect(response)

    def revoke(
        self, token: str, *, token_type_hint: Optional[TokenTypeHint] = None
    ) -> None:
        """Отозвать access- или refresh-токен (RFC 7009)."""
        response = self._client.post(
            REVOKE_ENDPOINT,
            data=self._revoke_form(token, token_type_hint),
            auth=self._basic,
        )
        self._raise_for_oauth(response)

    def get_userinfo(self, access_token: str) -> OidcUserInfo:
        """Claim'ы пользователя из userinfo-эндпоинта по access-токену."""
        response = self._client.get(
            USERINFO_ENDPOINT, headers=self._bearer(access_token)
        )
        return self._parse_userinfo(response)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "TidOAuth":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
