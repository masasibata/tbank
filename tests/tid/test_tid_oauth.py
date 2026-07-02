import base64
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from tbank.core.errors import AuthenticationError, ValidationError
from tbank.tid.aio import TidOAuth as AsyncTidOAuth
from tbank.tid.enums import TokenTypeHint
from tbank.tid.sync import TidOAuth as SyncTidOAuth

BASIC = "Basic " + base64.b64encode(b"cid:csec").decode()


def _async_oauth(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncTidOAuth("cid", "csec", client=client)


def _sync_oauth(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SyncTidOAuth("cid", "csec", client=client)


def _form(request: httpx.Request) -> dict:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


def test_build_authorization_url_full_and_minimal():
    # build_authorization_url — чистая сборка URL без IO; клиент подставляем мок.
    oauth = _sync_oauth(lambda request: httpx.Response(200))
    url = oauth.build_authorization_url(
        redirect_uri="https://app/cb",
        scope=["openid", "phone"],
        state="st",
        code_challenge="cc",
        prompt="consent",
    )
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    assert parsed.netloc == "id.tbank.ru" and parsed.path == "/auth/authorize"
    assert q["response_type"] == ["code"]
    assert q["client_id"] == ["cid"]
    assert q["redirect_uri"] == ["https://app/cb"]
    assert q["scope"] == ["openid phone"]
    assert q["state"] == ["st"]
    assert q["code_challenge"] == ["cc"]
    assert q["code_challenge_method"] == ["S256"]
    assert q["prompt"] == ["consent"]

    minimal = oauth.build_authorization_url(
        redirect_uri="https://app/cb", scope="openid"
    )
    mq = parse_qs(urlparse(minimal).query)
    assert "state" not in mq and "code_challenge" not in mq
    assert mq["scope"] == ["openid"]


def test_token_response_revalidation_keeps_raw():
    from tbank.tid.models import TokenResponse

    original = TokenResponse.model_validate(
        {"access_token": "a", "token_type": "Bearer", "custom": "x"}
    )
    assert original.raw["custom"] == "x"
    # вход, где raw уже задан явно, не перезатирается (ветка fallback валидатора)
    preset = TokenResponse.model_validate(
        {"access_token": "a", "token_type": "Bearer", "raw": {"k": "v"}}
    )
    assert preset.raw == {"k": "v"}


async def test_fetch_token_uses_basic_auth_and_form():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["ct"] = request.headers["content-type"]
        seen["form"] = _form(request)
        return httpx.Response(
            200,
            json={
                "access_token": "at",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "rt",
                "id_token": "idt",
                "scope": "openid phone",
            },
        )

    oauth = _async_oauth(handler)
    token = await oauth.fetch_token("the-code", "https://app/cb", code_verifier="ver")
    assert seen["url"] == "https://id.tbank.ru/auth/token"
    assert seen["auth"] == BASIC
    assert seen["ct"] == "application/x-www-form-urlencoded"
    assert seen["form"] == {
        "grant_type": "authorization_code",
        "code": "the-code",
        "redirect_uri": "https://app/cb",
        "code_verifier": "ver",
    }
    assert token.access_token == "at"
    assert token.refresh_token == "rt"
    assert token.expires_in == 3600
    await oauth.aclose()


async def test_refresh_and_client_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        form = _form(request)
        return httpx.Response(
            200,
            json={
                "access_token": "a",
                "token_type": "Bearer",
                "scope": form.get("scope", ""),
            },
        )

    oauth = _async_oauth(handler)

    def refresh_handler(request):
        assert _form(request) == {"grant_type": "refresh_token", "refresh_token": "rt"}
        return httpx.Response(200, json={"access_token": "a2", "token_type": "Bearer"})

    oauth2 = _async_oauth(refresh_handler)
    refreshed = await oauth2.refresh_token("rt")
    assert refreshed.access_token == "a2"
    await oauth2.aclose()

    cc = await oauth.fetch_client_credentials_token(scope=["openid"])
    assert cc.scope == "openid"
    cc_none = await oauth.fetch_client_credentials_token()
    assert cc_none.access_token == "a"
    await oauth.aclose()


async def test_introspect_scopes_property():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://id.tbank.ru/auth/introspect"
        assert request.headers["Authorization"] == BASIC
        assert _form(request) == {"token": "at"}
        return httpx.Response(
            200,
            json={
                "active": True,
                "scope": "openid phone profile",
                "client_id": "cid",
                "sub": "user-1",
                "exp": 1893456000,
                "custom_claim": "x",
            },
        )

    oauth = _async_oauth(handler)
    intro = await oauth.introspect("at")
    assert intro.active is True
    assert intro.scopes == ["openid", "phone", "profile"]
    assert intro.sub == "user-1"
    assert intro.raw["custom_claim"] == "x"  # нестандартный claim сохранён в raw
    await oauth.aclose()


def test_introspect_inactive_has_empty_scopes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"active": False})

    oauth = _sync_oauth(handler)
    intro = oauth.introspect("at")
    assert intro.active is False
    assert intro.scopes == []
    oauth.close()


async def test_revoke_with_and_without_hint_returns_none():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://id.tbank.ru/auth/revoke"
        seen["form"] = _form(request)
        return httpx.Response(200, text="")

    oauth = _async_oauth(handler)
    assert await oauth.revoke("rt", token_type_hint=TokenTypeHint.REFRESH_TOKEN) is None
    assert seen["form"] == {"token": "rt", "token_type_hint": "refresh_token"}
    assert await oauth.revoke("at") is None
    assert seen["form"] == {"token": "at"}
    await oauth.aclose()


async def test_get_userinfo_uses_bearer():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://id.tbank.ru/userinfo/userinfo"
        assert request.headers["Authorization"] == "Bearer at"
        return httpx.Response(
            200,
            json={
                "sub": "user-1",
                "given_name": "Иван",
                "family_name": "Петров",
                "phone_number": "+70000000000",
            },
        )

    oauth = _async_oauth(handler)
    info = await oauth.get_userinfo("at")
    assert info.sub == "user-1" and info.given_name == "Иван"
    await oauth.aclose()


async def test_oauth_error_mapping():
    def invalid_grant(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": "invalid_grant", "error_description": "code expired"},
        )

    oauth = _async_oauth(invalid_grant)
    with pytest.raises(ValidationError) as exc:
        await oauth.fetch_token("bad", "https://app/cb")
    assert exc.value.code == "invalid_grant"
    await oauth.aclose()

    def invalid_client(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": "invalid_client", "error_description": "bad secret"},
        )

    oauth2 = _async_oauth(invalid_client)
    with pytest.raises(AuthenticationError):
        await oauth2.introspect("at")
    await oauth2.aclose()


async def test_oauth_error_non_json_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="gateway down")

    oauth = _async_oauth(handler)
    with pytest.raises(Exception) as exc:
        await oauth.refresh_token("rt")
    assert "gateway down" in str(exc.value)
    await oauth.aclose()


async def test_async_context_manager():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "a", "token_type": "Bearer"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AsyncTidOAuth("cid", "csec", client=client) as oauth:
        token = await oauth.refresh_token("rt")
    assert token.access_token == "a"


def test_sync_context_manager_and_flow():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = urlparse(str(request.url)).path
        if path == "/auth/token":
            assert request.headers["Authorization"] == BASIC
            seen["token_form"] = _form(request)
            return httpx.Response(
                200, json={"access_token": "a", "token_type": "Bearer"}
            )
        if path == "/auth/revoke":
            seen["revoke_form"] = _form(request)
            return httpx.Response(200, text="")
        if path == "/userinfo/userinfo":
            return httpx.Response(200, json={"sub": "s"})
        raise AssertionError(path)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with SyncTidOAuth("cid", "csec", client=client) as oauth:
        assert oauth.fetch_token("c", "https://app/cb").access_token == "a"
        assert oauth.refresh_token("rt").access_token == "a"
        assert seen["token_form"]["grant_type"] == "refresh_token"
        assert oauth.fetch_client_credentials_token(scope="openid").access_token == "a"
        assert seen["token_form"] == {
            "grant_type": "client_credentials",
            "scope": "openid",
        }
        assert oauth.get_userinfo("a").sub == "s"
        assert oauth.revoke("rt", token_type_hint=TokenTypeHint.ACCESS_TOKEN) is None
        assert seen["revoke_form"] == {"token": "rt", "token_type_hint": "access_token"}
