import json

import httpx

from tbank.acquiring.aio import AcquiringClient as AsyncAcquiringClient
from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.sync import AcquiringClient as SyncAcquiringClient
from tbank.core.transport import AsyncTransport, SyncTransport


def _async_client(handler):
    transport = AsyncTransport(
        base_url="https://securepay.tinkoff.ru/v2",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        auth=TokenSignatureAuth("T", "p"),
    )
    return AsyncAcquiringClient(terminal_key="T", password="p", transport=transport)


def _sync_client(handler):
    transport = SyncTransport(
        base_url="https://securepay.tinkoff.ru/v2",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        auth=TokenSignatureAuth("T", "p"),
    )
    return SyncAcquiringClient(terminal_key="T", password="p", transport=transport)


async def test_tinkoff_pay_status_is_bodyless_get_without_token():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["content"] = request.content
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "Params": {"Allowed": True, "Version": "2.0"},
            },
        )

    client = _async_client(handler)
    resp = await client.get_tinkoff_pay_status()
    assert seen["method"] == "GET"
    assert seen["path"] == "/v2/TinkoffPay/terminals/T/status"
    assert seen["content"] == b""  # без тела и без Token
    assert resp.params is not None
    assert resp.params.allowed is True
    assert resp.params.version == "2.0"
    await client.aclose()


async def test_tinkoff_pay_link_parses_redirect_and_qr():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/TinkoffPay/transactions/700/versions/2.0/link"
        assert request.content == b""
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "Params": {
                    "RedirectUrl": "https://www.tinkoff.ru/tpay/700",
                    "WebQR": "https://qr/x",
                },
            },
        )

    client = _async_client(handler)
    resp = await client.get_tinkoff_pay_link("700", "2.0")
    assert resp.params is not None
    assert resp.params.redirect_url == "https://www.tinkoff.ru/tpay/700"
    assert resp.params.web_qr == "https://qr/x"
    await client.aclose()


async def test_tinkoff_pay_qr_returns_svg_text():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/TinkoffPay/700/QR"
        return httpx.Response(
            200, text="<svg>QR</svg>", headers={"content-type": "image/svg+xml"}
        )

    client = _async_client(handler)
    svg = await client.get_tinkoff_pay_qr("700")
    assert svg == "<svg>QR</svg>"
    await client.aclose()


async def test_sber_pay_link_and_qr():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/QR"):
            return httpx.Response(200, text="<svg/>")
        assert request.url.path == "/v2/SberPay/transactions/700/link"
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "Params": {"RedirectUrl": "https://sber/700"},
            },
        )

    client = _async_client(handler)
    link = await client.get_sber_pay_link("700")
    assert link.params is not None and link.params.redirect_url == "https://sber/700"
    assert await client.get_sber_pay_qr("700") == "<svg/>"
    await client.aclose()


async def test_mir_pay_deeplink_is_signed_post():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "Params": {"Deeplink": "mirpay://700"},
            },
        )

    client = _async_client(handler)
    resp = await client.get_mir_pay_deeplink("700")
    assert seen["path"] == "/v2/MirPay/GetDeepLink"
    assert seen["body"]["PaymentId"] == "700"
    assert seen["body"]["TerminalKey"] == "T"
    assert "Token" in seen["body"]  # MirPay подписывается
    assert resp.params is not None and resp.params.deeplink == "mirpay://700"
    await client.aclose()


async def test_check_order_parses_payments_and_both_rrn_spellings():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/CheckOrder"
        body = json.loads(request.content)
        assert body["OrderId"] == "A-1"
        assert "Token" in body
        return httpx.Response(
            200,
            json={
                "Success": True,
                "ErrorCode": "0",
                "OrderId": "A-1",
                "Payments": [
                    {
                        "PaymentId": "700",
                        "Amount": 19200,
                        "Status": "CONFIRMED",
                        "RRN": "12345",
                        "Success": True,
                        "ErrorCode": "0",
                    },
                    {
                        "PaymentId": "701",
                        "Status": "AUTH_FAIL",
                        "Rrn": "67890",
                        "Success": False,
                        "ErrorCode": "1051",
                    },
                ],
            },
        )

    client = _async_client(handler)
    resp = await client.check_order("A-1")
    assert len(resp.payments) == 2
    assert resp.payments[0].payment_id == "700"
    assert resp.payments[0].amount == 19200
    assert resp.payments[0].rrn == "12345"  # из "RRN"
    assert resp.payments[1].status == "AUTH_FAIL"
    assert resp.payments[1].rrn == "67890"  # из "Rrn"
    await client.aclose()


async def test_resend_signs_empty_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"Success": True, "ErrorCode": "0", "Count": 3})

    client = _async_client(handler)
    resp = await client.resend()
    assert seen["body"]["TerminalKey"] == "T"
    assert "Token" in seen["body"]  # Resend подписывается (Password+TerminalKey)
    assert resp.count == 3
    await client.aclose()


def test_sync_altpay_and_service_methods():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/status"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "Params": {"Allowed": True, "Version": "2.0"},
                },
            )
        if path.endswith("/QR"):
            return httpx.Response(200, text="<svg/>")
        if path.endswith("/Resend"):
            return httpx.Response(
                200, json={"Success": True, "ErrorCode": "0", "Count": 2}
            )
        if path.endswith("/link") or path.endswith("/GetDeepLink"):
            return httpx.Response(
                200,
                json={
                    "Success": True,
                    "ErrorCode": "0",
                    "Params": {"RedirectUrl": "u", "Deeplink": "d"},
                },
            )
        return httpx.Response(
            200,
            json={"Success": True, "ErrorCode": "0", "OrderId": "A-1", "Payments": []},
        )

    client = _sync_client(handler)
    assert client.get_tinkoff_pay_status().params.version == "2.0"
    assert client.get_tinkoff_pay_qr("700") == "<svg/>"
    assert client.get_tinkoff_pay_link("700", "2.0").params.redirect_url == "u"
    assert client.get_sber_pay_link("700").params.redirect_url == "u"
    assert client.get_sber_pay_qr("700") == "<svg/>"
    assert client.get_mir_pay_deeplink("700").params.deeplink == "d"
    assert client.resend().count == 2
    assert client.check_order("A-1").order_id == "A-1"
    client.close()
