import json
from decimal import Decimal

import httpx

from tbank.business.aio import BusinessClient as AsyncBusinessClient
from tbank.business.enums import InvoiceStatus, SbpQrStatus, SbpQrType
from tbank.business.models import (
    CreateOnetimeQrRequest,
    CreateReusableQrRequest,
    InvoiceItem,
    InvoicePayer,
    SendInvoiceRequest,
)
from tbank.business.sync import BusinessClient as SyncBusinessClient
from tbank.core.auth import BearerAuth
from tbank.core.transport import AsyncTransport, SyncTransport


def _async_client(handler):
    return AsyncBusinessClient(
        token="TKN",
        transport=AsyncTransport(
            base_url="https://business.tbank.ru/openapi",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            auth=BearerAuth("TKN"),
        ),
    )


def _sync_client(handler):
    return SyncBusinessClient(
        token="TKN",
        transport=SyncTransport(
            base_url="https://business.tbank.ru/openapi",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            auth=BearerAuth("TKN"),
        ),
    )


async def test_send_invoice_serializes_items_and_parses_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "pdfUrl": "https://x/inv.pdf",
                "invoiceId": "inv-1",
                "incomingInvoiceUrl": "https://x/pay",
            },
        )

    client = _async_client(handler)
    req = SendInvoiceRequest(
        invoice_number="101",
        items=[
            InvoiceItem(
                name="Товар",
                price=Decimal("100.50"),
                unit="Шт",
                vat="20",
                amount=Decimal("2"),
            )
        ],
        payer=InvoicePayer(name="ООО Ромашка", inn="7700000000"),
    )
    resp = await client.send_invoice(req)
    assert seen["path"] == "/openapi/api/v1/invoice/send"
    assert seen["body"]["invoiceNumber"] == "101"
    item = seen["body"]["items"][0]
    assert item["price"] == 100.5 and isinstance(item["price"], float)
    assert item["vat"] == "20"
    assert seen["body"]["payer"]["inn"] == "7700000000"
    assert resp.invoice_id == "inv-1"
    assert resp.pdf_url == "https://x/inv.pdf"
    await client.aclose()


async def test_get_invoice_info_parses_status():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openapi/api/v1/openapi/invoice/inv-1/info"
        return httpx.Response(200, json={"status": "EXECUTED"})

    client = _async_client(handler)
    info = await client.get_invoice_info("inv-1")
    assert info.status is InvoiceStatus.EXECUTED
    await client.aclose()


async def test_create_onetime_qr_sends_number_sum_and_parses():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "qrId": "qr-1",
                "paymentUrl": "https://b2b.cbrpay.ru/x",
                "type": "Onetime",
                "status": "Ready",
                "accountNumber": "40802810000000000001",
                "sum": 1500.00,
            },
        )

    client = _async_client(handler)
    qr = await client.create_onetime_qr(
        CreateOnetimeQrRequest(sum=Decimal("1500.00"), purpose="Оплата", ttl=3)
    )
    assert seen["path"] == "/openapi/api/v1/b2b/qr/onetime"
    assert seen["body"]["sum"] == 1500.0 and isinstance(seen["body"]["sum"], float)
    assert seen["body"]["ttl"] == 3
    assert qr.qr_id == "qr-1"
    assert qr.type is SbpQrType.ONETIME
    assert qr.status is SbpQrStatus.READY
    assert qr.sum == Decimal("1500.00")
    await client.aclose()


async def test_create_reusable_qr():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openapi/api/v1/b2b/qr/reusable"
        return httpx.Response(
            200,
            json={
                "qrId": "qr-2",
                "paymentUrl": "https://b2b.cbrpay.ru/y",
                "type": "Reusable",
                "status": "Ready",
                "accountNumber": "40802810000000000001",
            },
        )

    client = _async_client(handler)
    qr = await client.create_reusable_qr(CreateReusableQrRequest(purpose="Донат"))
    assert qr.type is SbpQrType.REUSABLE
    await client.aclose()


async def test_get_qr_info_passes_with_image_and_parses_image():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "qrId": "qr-1",
                "paymentUrl": "https://b2b.cbrpay.ru/x",
                "type": "Onetime",
                "status": "Paid",
                "accountNumber": "40802810000000000001",
                "image": {"content": "SW1hZ2U=", "mediaType": "image/png"},
            },
        )

    client = _async_client(handler)
    qr = await client.get_qr_info("qr-1", with_image=True)
    assert seen["params"]["withImage"] == "true"
    assert qr.status is SbpQrStatus.PAID
    assert qr.image is not None and qr.image.media_type == "image/png"
    await client.aclose()


def test_sync_send_invoice_and_qr():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/invoice/send"):
            return httpx.Response(
                200, json={"pdfUrl": "https://x/i.pdf", "invoiceId": "i-9"}
            )
        return httpx.Response(
            200,
            json={
                "qrId": "q-9",
                "paymentUrl": "u",
                "type": "Onetime",
                "status": "Ready",
                "accountNumber": "40802810000000000001",
            },
        )

    client = _sync_client(handler)
    inv = client.send_invoice(SendInvoiceRequest(invoice_number="9"))
    assert inv.invoice_id == "i-9"
    qr = client.create_onetime_qr(
        CreateOnetimeQrRequest(sum=Decimal("10"), purpose="p", ttl=1)
    )
    assert qr.qr_id == "q-9"
    client.close()


def test_sync_invoice_info_reusable_and_qr_info():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/info") and "invoice" in path:
            return httpx.Response(200, json={"status": "DRAFT"})
        if path.endswith("/reusable"):
            return httpx.Response(
                200,
                json={
                    "qrId": "r1",
                    "paymentUrl": "u",
                    "type": "Reusable",
                    "status": "Ready",
                    "accountNumber": "40802810000000000001",
                },
            )
        return httpx.Response(
            200,
            json={
                "qrId": "q1",
                "paymentUrl": "u",
                "type": "Onetime",
                "status": "Cancelled",
                "accountNumber": "40802810000000000001",
            },
        )

    client = _sync_client(handler)
    assert client.get_invoice_info("i1").status is InvoiceStatus.DRAFT
    assert (
        client.create_reusable_qr(CreateReusableQrRequest(purpose="x")).type
        is SbpQrType.REUSABLE
    )
    assert client.get_qr_info("q1").status is SbpQrStatus.CANCELLED
    client.close()
