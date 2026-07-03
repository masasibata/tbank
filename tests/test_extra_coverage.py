"""Дополнительные тесты на непокрытые ветки: ретраи, ошибки сети/таймаута,
контекст-менеджеры, jitter и sync-методы клиента."""

import httpx
import pytest

from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.sync import AcquiringClient as SyncAcquiringClient
from tbank.core.client import BaseAsyncClient, BaseSyncClient
from tbank.core.endpoint import Endpoint
from tbank.core.errors import TBankNetworkError, TBankTimeoutError
from tbank.core.models import TBankModel
from tbank.core.retry import RetryPolicy, compute_delay
from tbank.core.transport import AsyncTransport, SyncTransport

FAST = RetryPolicy(attempts=3, backoff_base=0.0, jitter=False)


def _seq_handler(events):
    """events: элементы — либо int-статус, либо Exception (будет брошено)."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        event = events[min(calls["n"], len(events) - 1)]
        calls["n"] += 1
        if isinstance(event, Exception):
            raise event
        return httpx.Response(event, json={"ok": True})

    return handler, calls


# --- transport: async ---


_PROXY_VARS = (
    "all_proxy",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
)


async def test_async_default_client_constructed_and_closed(monkeypatch):
    for var in _PROXY_VARS:
        monkeypatch.delenv(var, raising=False)
    transport = AsyncTransport(base_url="https://x/v2")
    await transport.aclose()


async def test_async_retries_on_network_error_then_succeeds():
    handler, calls = _seq_handler([httpx.ConnectError("boom"), 200])
    transport = AsyncTransport(
        base_url="https://x/v2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        retry=FAST,
    )
    resp = await transport.request("GET", "/GetState")
    assert resp.status_code == 200
    assert calls["n"] == 2
    await transport.aclose()


async def test_async_timeout_raises_after_retries():
    handler, _ = _seq_handler([httpx.ConnectTimeout("slow")])
    transport = AsyncTransport(
        base_url="https://x/v2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        retry=RetryPolicy(attempts=2, backoff_base=0.0, jitter=False),
    )
    with pytest.raises(TBankTimeoutError):
        await transport.request("POST", "/Init", json={"a": 1})
    await transport.aclose()


async def test_async_context_manager():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    async with AsyncTransport(
        base_url="https://x/v2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as transport:
        assert (await transport.request("GET", "/ping")).status_code == 200


# --- transport: sync ---


def test_sync_default_client_constructed_and_closed(monkeypatch):
    for var in _PROXY_VARS:
        monkeypatch.delenv(var, raising=False)
    transport = SyncTransport(base_url="https://x/v2")
    transport.close()


def test_sync_retries_on_503_then_succeeds():
    handler, calls = _seq_handler([503, 200])
    transport = SyncTransport(
        base_url="https://x/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        retry=FAST,
    )
    resp = transport.request("GET", "/GetState")
    assert resp.status_code == 200
    assert calls["n"] == 2
    transport.close()


def test_sync_network_error_raises():
    handler, _ = _seq_handler([httpx.ConnectError("boom")])
    transport = SyncTransport(
        base_url="https://x/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        retry=RetryPolicy(attempts=1),
    )
    with pytest.raises(TBankNetworkError):
        transport.request("POST", "/Init", json={"a": 1})
    transport.close()


def test_sync_context_manager():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    with SyncTransport(
        base_url="https://x/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as transport:
        assert transport.request("GET", "/ping").status_code == 200


# --- transport: доп. ветки ---


async def test_async_network_error_exhausted_raises():
    handler, _ = _seq_handler([httpx.ConnectError("boom")])
    transport = AsyncTransport(
        base_url="https://x/v2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        retry=RetryPolicy(attempts=1),
    )
    with pytest.raises(TBankNetworkError):
        await transport.request("POST", "/Init", json={"a": 1})
    await transport.aclose()


def test_sync_timeout_raises_after_retries():
    handler, _ = _seq_handler([httpx.ConnectTimeout("slow")])
    transport = SyncTransport(
        base_url="https://x/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        retry=RetryPolicy(attempts=2, backoff_base=0.0, jitter=False),
    )
    with pytest.raises(TBankTimeoutError):
        transport.request("POST", "/Init", json={"a": 1})
    transport.close()


def test_sync_retries_on_network_error_then_succeeds():
    handler, calls = _seq_handler([httpx.ConnectError("boom"), 200])
    transport = SyncTransport(
        base_url="https://x/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        retry=FAST,
    )
    resp = transport.request("GET", "/GetState")
    assert resp.status_code == 200
    assert calls["n"] == 2
    transport.close()


def test_retry_after_header_is_parsed():
    events = [429, 200]
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        idx = min(calls["n"], len(events) - 1)
        calls["n"] += 1
        if events[idx] == 429:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={})
        return httpx.Response(200, json={"ok": True})

    transport = SyncTransport(
        base_url="https://x/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        retry=FAST,
    )
    assert transport.request("GET", "/ping").status_code == 200
    assert calls["n"] == 2
    transport.close()


# --- retry jitter ---


def test_delay_with_jitter_within_bounds():
    policy = RetryPolicy(backoff_base=1.0, jitter=True)
    for _ in range(20):
        delay = compute_delay(policy, attempt=1)
        assert 0.5 <= delay <= 1.0


# --- base client context managers ---


class _Req(TBankModel):
    order_id: str


class _Resp(TBankModel):
    ok: bool = True


_EP = Endpoint("POST", "/Init", _Resp, _Req)


def _ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"ok": True})


async def test_async_client_context_manager_closes():
    transport = AsyncTransport(
        base_url="https://x/v2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_ok_handler)),
    )
    async with BaseAsyncClient(transport) as client:
        await client._call(_EP, _Req(order_id="A-1"))


def test_sync_client_context_manager_closes():
    transport = SyncTransport(
        base_url="https://x/v2",
        client=httpx.Client(transport=httpx.MockTransport(_ok_handler)),
    )
    with BaseSyncClient(transport) as client:
        client._call(_EP, _Req(order_id="A-1"))


# --- sync acquiring client: get_state / confirm / cancel ---


def test_sync_get_state_confirm_cancel_paths():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "PaymentId": "700",
                "Status": "CONFIRMED",
            },
        )

    transport = SyncTransport(
        base_url="https://securepay.tinkoff.ru/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        auth=TokenSignatureAuth("T", "p"),
    )
    client = SyncAcquiringClient(terminal_key="T", password="p", transport=transport)
    client.get_state("700")
    client.confirm("700")
    client.cancel("700", amount=100)
    assert seen == ["/v2/GetState", "/v2/Confirm", "/v2/Cancel"]
    client.close()
