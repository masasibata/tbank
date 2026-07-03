from __future__ import annotations

from typing import List, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import CertTypes, SyncTransport, VerifyTypes
from tbank.core.urls import PROD_URL
from tbank.tid._endpoints import ADDRESSES_PATH as _ADDRESSES_PATH
from tbank.tid._endpoints import BLACKLIST as _BLACKLIST
from tbank.tid._endpoints import COMPANY as _COMPANY
from tbank.tid._endpoints import DEBIT_ACCOUNTS as _DEBIT_ACCOUNTS
from tbank.tid._endpoints import DELEGATED as _DELEGATED
from tbank.tid._endpoints import DETAIL_COUNTERS as _DETAIL_COUNTERS
from tbank.tid._endpoints import DRIVER_LICENSES as _DRIVER_LICENSES
from tbank.tid._endpoints import FOREIGN_AGENT as _FOREIGN_AGENT
from tbank.tid._endpoints import IDENTIFICATION_STATUS as _IDENTIFICATION_STATUS
from tbank.tid._endpoints import INN as _INN
from tbank.tid._endpoints import PASSPORT_PATH as _PASSPORT_PATH
from tbank.tid._endpoints import PDL as _PDL
from tbank.tid._endpoints import REMOTE_ID as _REMOTE_ID
from tbank.tid._endpoints import SELF_EMPLOYED as _SELF_EMPLOYED
from tbank.tid._endpoints import SET_COUNTERS as _SET_COUNTERS
from tbank.tid._endpoints import SIGNER as _SIGNER
from tbank.tid._endpoints import SNILS as _SNILS
from tbank.tid._endpoints import SUBSCRIPTION as _SUBSCRIPTION
from tbank.tid._endpoints import SUBSCRIPTION_GRADE as _SUBSCRIPTION_GRADE
from tbank.tid._endpoints import USERINFO as _USERINFO
from tbank.tid._endpoints import cobrand_path as _cobrand_path
from tbank.tid._endpoints import personal_data_path as _personal_data_path
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
        cert: Optional[CertTypes] = None,
        verify: VerifyTypes = True,
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
        return self._get(_PASSPORT_PATH, PassportData, params=params)

    def get_driver_licenses(self) -> DriverLicensesResponse:
        """Водительские удостоверения."""
        return self._call(_DRIVER_LICENSES)

    def get_addresses(self, address_type: Optional[str] = None) -> AddressesResponse:
        """Адреса физлица (опционально фильтр по типу адреса)."""
        params = {"addressType": address_type} if address_type else None
        return self._get(_ADDRESSES_PATH, AddressesResponse, params=params)

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
        return self._get(_cobrand_path(program_id), CobrandResponse)

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
        return self._get(_personal_data_path(request_id), IdentificationData)

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
