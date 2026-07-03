import httpx

from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport, SyncTransport


def _counting_handler(statuses):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        idx = calls["n"]
        calls["n"] += 1
        return httpx.Response(statuses[min(idx, len(statuses) - 1)], json={"ok": True})

    return handler, calls


async def test_async_get_retries_on_503_then_succeeds():
    handler, calls = _counting_handler([503, 200])
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = AsyncTransport(
        base_url="https://x/v2",
        client=client,
        retry=RetryPolicy(attempts=3, backoff_base=0.0, jitter=False),
    )
    resp = await transport.request("GET", "/GetState")
    assert resp.status_code == 200
    assert calls["n"] == 2
    await transport.aclose()


async def test_async_post_without_idempotency_key_not_retried_on_503():
    handler, calls = _counting_handler([503, 200])
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = AsyncTransport(
        base_url="https://x/v2",
        client=client,
        retry=RetryPolicy(attempts=3, backoff_base=0.0, jitter=False),
    )
    resp = await transport.request("POST", "/Init", json={"a": 1})
    assert resp.status_code == 503
    assert calls["n"] == 1
    await transport.aclose()


async def test_async_post_with_idempotency_key_retried_on_503():
    handler, calls = _counting_handler([503, 200])
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = AsyncTransport(
        base_url="https://x/v2",
        client=client,
        retry=RetryPolicy(attempts=3, backoff_base=0.0, jitter=False),
    )
    resp = await transport.request(
        "POST", "/Init", json={"a": 1}, headers={"Idempotency-Key": "k-1"}
    )
    assert resp.status_code == 200
    assert calls["n"] == 2
    await transport.aclose()


def test_sync_post_retried_on_429_despite_non_idempotency():
    handler, calls = _counting_handler([429, 200])
    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = SyncTransport(
        base_url="https://x/v2",
        client=client,
        retry=RetryPolicy(attempts=3, backoff_base=0.0, jitter=False),
    )
    resp = transport.request("POST", "/Init", json={"a": 1})
    assert resp.status_code == 200
    assert calls["n"] == 2
    transport.close()


def test_sync_post_retried_on_503_with_optin_flag():
    handler, calls = _counting_handler([503, 200])
    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = SyncTransport(
        base_url="https://x/v2",
        client=client,
        retry=RetryPolicy(
            attempts=3, backoff_base=0.0, jitter=False, retry_non_idempotent=True
        ),
    )
    resp = transport.request("POST", "/Init", json={"a": 1})
    assert resp.status_code == 200
    assert calls["n"] == 2
    transport.close()


def test_sync_passes_headers_and_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"ok": True})

    from tbank.core.auth import BearerAuth

    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = SyncTransport(
        base_url="https://x/v2", client=client, auth=BearerAuth("TKN")
    )
    transport.request("POST", "/GetState", json={"a": 1})
    assert seen["url"] == "https://x/v2/GetState"
    assert seen["auth"] == "Bearer TKN"
    transport.close()
