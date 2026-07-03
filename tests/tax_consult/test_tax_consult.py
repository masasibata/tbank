import json

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.tax_consult.aio import SECURED_URL, TaxConsultClient
from tbank.tax_consult.enums import ChatAuthorType, RequestStatus, RequestType
from tbank.tax_consult.models import SendMessageRequest
from tbank.tax_consult.sync import TaxConsultClient as SyncClient


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=SECURED_URL, client=client, auth=BearerAuth("T"))


def _client(handler):
    return TaxConsultClient(token="T", transport=_transport(handler))


async def test_get_request():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        assert request.url.path == "/api/v1/consult/requests/comment"
        assert request.url.params.get("taxRequestId") == "tr-1"
        return httpx.Response(
            200,
            json={
                "clientId": "c-1",
                "clientFullName": "Иван Петров",
                "requestType": "Comment",
                "status": "InProgress",
                "hasUnreadMessages": True,
                "casVersion": 7,
                "createdAt": "2026-06-01T10:00:00Z",
            },
        )

    req = await _client(handler).get_request("tr-1")
    assert req.request_type == RequestType.COMMENT
    assert req.status == RequestStatus.IN_PROGRESS
    assert req.cas_version == 7


async def test_get_chat_and_send():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chat"):
            assert request.url.params.get("limit") == "20"
            return httpx.Response(
                200,
                json={
                    "meta": {"offset": 0, "count": 1, "total": 1},
                    "values": [
                        {
                            "id": "m-1",
                            "authorType": "Client",
                            "createdAt": "2026-06-01T11:00:00Z",
                            "text": "Вопрос",
                            "attachments": [
                                {
                                    "id": "a-1",
                                    "name": "doc.pdf",
                                    "mime": "application/pdf",
                                    "size": 1024,
                                    "createdAt": "2026-06-01T11:00:00Z",
                                }
                            ],
                        }
                    ],
                },
            )
        assert request.url.path.endswith("/chat/send")
        assert json.loads(request.content)["text"] == "Ответ"
        return httpx.Response(200, json={})

    client = _client(handler)
    page = await client.get_chat("tr-1", limit=20, offset=0)
    assert page.values[0].author_type == ChatAuthorType.CLIENT
    assert page.values[0].attachments[0].size == 1024
    assert await client.send_message("tr-1", SendMessageRequest(text="Ответ")) is None


async def test_attachments_upload_download():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.path.endswith("/attachments/upload")
            assert request.headers["content-type"] == "application/octet-stream"
            assert request.headers["X-Content-File-Name"] == "doc.pdf"
            assert request.headers["X-Content-File-Type"] == "application/pdf"
            assert request.headers.get("X-Idempotency-Key")
            assert request.content == b"PDFBYTES"
            return httpx.Response(200, json={"attachmentId": "att-1"})
        assert request.url.params.get("attachmentId") == "att-1"
        return httpx.Response(200, content=b"PDFBYTES")

    client = _client(handler)
    uploaded = await client.upload_attachment(
        "tr-1", b"PDFBYTES", file_name="doc.pdf", file_type="application/pdf"
    )
    assert uploaded.attachment_id == "att-1"
    content = await client.download_attachment("tr-1", "att-1")
    assert content == b"PDFBYTES"


async def test_workflow_transitions():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.startswith("/api/v1/consult/requests/comment/workflow/")
        assert request.headers["If-Match"] == "7"
        assert request.url.params.get("taxRequestId") == "tr-1"
        seen["action"] = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json={"status": "Ready", "casVersion": 8})

    client = _client(handler)
    calls = [
        (client.start_review, "start-review"),
        (client.start_work, "start-work"),
        (client.request_clarification, "clarification"),
        (client.decline, "decline"),
        (client.cancel, "cancel"),
        (client.set_pending_payment, "pending-payment"),
        (client.confirm_payment, "payment-done"),
        (client.mark_ready, "ready"),
    ]
    for method, action in calls:
        state = await method("tr-1", 7)
        assert seen["action"] == action
        assert state.status == RequestStatus.READY
        assert state.cas_version == 8


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        await client.get_request("tr-1")
    assert exc.value.error_id == "e"


def test_sync_client():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/comment") and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "clientId": "c",
                    "clientFullName": "N",
                    "requestType": "Declaration",
                    "status": "New",
                    "hasUnreadMessages": False,
                    "casVersion": 1,
                    "createdAt": "2026-06-01T10:00:00Z",
                },
            )
        if "/workflow/" in request.url.path:
            return httpx.Response(200, json={"status": "Assigned", "casVersion": 2})
        return httpx.Response(500, text="boom")

    client = SyncClient(token="T", transport=_transport(handler, sync=True))
    assert client.get_request("tr-1").request_type == RequestType.DECLARATION
    assert client.start_review("tr-1", 1).cas_version == 2
    with pytest.raises(TBankAPIError):
        client.send_message("tr-1", SendMessageRequest(text="x"))
    client.close()


def _surface_handler(request: httpx.Request) -> httpx.Response:
    p, m = request.url.path, request.method
    if "/workflow/" in p:
        return httpx.Response(200, json={"status": "Ready", "casVersion": 9})
    if p.endswith("/comment") and m == "GET":
        return httpx.Response(
            200,
            json={
                "clientId": "c",
                "clientFullName": "N",
                "requestType": "Comment",
                "status": "New",
                "hasUnreadMessages": False,
                "casVersion": 1,
                "createdAt": "2026-06-01T10:00:00Z",
            },
        )
    if p.endswith("/chat") and m == "GET":
        return httpx.Response(
            200, json={"meta": {"offset": 0, "count": 0, "total": 0}, "values": []}
        )
    if p.endswith("/chat/send"):
        return httpx.Response(200, json={})
    if p.endswith("/attachments/upload"):
        return httpx.Response(200, json={"attachmentId": "att"})
    if p.endswith("/attachments"):
        return httpx.Response(200, content=b"BYTES")
    return httpx.Response(500)  # pragma: no cover


def test_sync_full_surface():
    client = SyncClient(token="T", transport=_transport(_surface_handler, sync=True))
    assert client.get_request("tr").cas_version == 1
    assert client.get_chat("tr", limit=10, offset=0).meta.total == 0
    assert client.send_message("tr", SendMessageRequest(text="x")) is None
    assert (
        client.upload_attachment(
            "tr", b"X", file_name="f", file_type="application/pdf"
        ).attachment_id
        == "att"
    )
    assert client.download_attachment("tr", "att") == b"BYTES"
    for method in (
        client.start_review,
        client.start_work,
        client.request_clarification,
        client.decline,
        client.cancel,
        client.set_pending_payment,
        client.confirm_payment,
        client.mark_ready,
    ):
        assert method("tr", 1).cas_version == 9
    client.close()
