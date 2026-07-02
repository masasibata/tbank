from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple, Union
from urllib.parse import urlencode

import httpx

from tbank.tid.enums import GrantType, TokenTypeHint
from tbank.tid.errors import error_from_oauth_response
from tbank.tid.models import IntrospectionResponse, OidcUserInfo, TokenResponse

Scope = Union[str, Sequence[str]]

ISSUER = "https://id.tbank.ru"
AUTHORIZE_ENDPOINT = f"{ISSUER}/auth/authorize"
TOKEN_ENDPOINT = f"{ISSUER}/auth/token"
INTROSPECT_ENDPOINT = f"{ISSUER}/auth/introspect"
REVOKE_ENDPOINT = f"{ISSUER}/auth/revoke"
USERINFO_ENDPOINT = f"{ISSUER}/userinfo/userinfo"


def _scope_str(scope: Optional[Scope]) -> Optional[str]:
    if scope is None:
        return None
    if isinstance(scope, str):
        return scope
    return " ".join(scope)


class _OAuthBase:
    """Не-IO ядро OAuth 2.0 / OIDC клиента T-ID (id.tbank.ru).

    Аутентификация клиента — client_secret_basic (HTTP Basic client_id:client_secret),
    как объявлено в OIDC discovery. Токен-эндпоинты принимают form-urlencoded.
    """

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    # --- сборка запроса ---

    @property
    def _basic(self) -> Tuple[str, str]:
        return (self._client_id, self._client_secret)

    def build_authorization_url(
        self,
        *,
        redirect_uri: str,
        scope: Scope,
        state: Optional[str] = None,
        response_type: str = "code",
        code_challenge: Optional[str] = None,
        code_challenge_method: str = "S256",
        **extra: str,
    ) -> str:
        """Собрать URL страницы согласия T-ID для редиректа пользователя.

        ``scope`` — строка или список скоупов. Для PKCE передайте ``code_challenge``.
        Дополнительные query-параметры можно добавить через ``extra``.
        """
        params: Dict[str, str] = {
            "response_type": response_type,
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
        }
        scope_value = _scope_str(scope)
        if scope_value:
            params["scope"] = scope_value
        if state is not None:
            params["state"] = state
        if code_challenge is not None:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method
        params.update({k: v for k, v in extra.items() if v is not None})
        return f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}"

    @staticmethod
    def _code_form(
        code: str, redirect_uri: str, code_verifier: Optional[str]
    ) -> Dict[str, str]:
        form = {
            "grant_type": GrantType.AUTHORIZATION_CODE.value,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        if code_verifier is not None:
            form["code_verifier"] = code_verifier
        return form

    @staticmethod
    def _refresh_form(refresh_token: str) -> Dict[str, str]:
        return {
            "grant_type": GrantType.REFRESH_TOKEN.value,
            "refresh_token": refresh_token,
        }

    @staticmethod
    def _client_credentials_form(scope: Optional[Scope]) -> Dict[str, str]:
        form = {"grant_type": GrantType.CLIENT_CREDENTIALS.value}
        scope_value = _scope_str(scope)
        if scope_value:
            form["scope"] = scope_value
        return form

    @staticmethod
    def _revoke_form(
        token: str, token_type_hint: Optional[TokenTypeHint]
    ) -> Dict[str, str]:
        form = {"token": token}
        if token_type_hint is not None:
            form["token_type_hint"] = token_type_hint.value
        return form

    # --- разбор ответа ---

    @staticmethod
    def _raise_for_oauth(response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise error_from_oauth_response(response)

    def _parse_token(self, response: httpx.Response) -> TokenResponse:
        self._raise_for_oauth(response)
        return TokenResponse.model_validate(response.json())

    def _parse_introspect(self, response: httpx.Response) -> IntrospectionResponse:
        self._raise_for_oauth(response)
        return IntrospectionResponse.model_validate(response.json())

    def _parse_userinfo(self, response: httpx.Response) -> OidcUserInfo:
        self._raise_for_oauth(response)
        return OidcUserInfo.model_validate(response.json())

    @staticmethod
    def _bearer(access_token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}
