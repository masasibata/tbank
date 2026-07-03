import json

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.shopping.aio import SECURED_URL, ShoppingClient
from tbank.shopping.models import SendMessageRequest
from tbank.shopping.sync import ShoppingClient as SyncClient


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=SECURED_URL, client=client, auth=BearerAuth("T"))


def _client(handler):
    return ShoppingClient(token="T", transport=_transport(handler))


async def test_chats_and_messages():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        p = request.url.path
        if p == "/api/v1/shopping/shops/S/chats":
            return httpx.Response(
                200,
                json={
                    "chats": [{"chatId": "C", "createdAt": "2026-01-01T00:00:00+03:00"}]
                },
            )
        if p == "/api/v1/shopping/shops/S/chats/C":
            return httpx.Response(
                200,
                json={
                    "chatId": "C",
                    "createdAt": "2026-01-01T00:00:00+03:00",
                    "description": "Заказ №5",
                },
            )
        if p.endswith("/messages") and request.method == "GET":
            assert request.url.params.get("limit") == "50"
            return httpx.Response(
                200,
                json={
                    "messages": [
                        {
                            "messageId": "m-1",
                            "author": {"name": "Иван"},
                            "createdAt": "2026-01-02T00:00:00+03:00",
                            "message": "Привет",
                            "files": [
                                {
                                    "id": "fi-1",
                                    "name": "img.png",
                                    "size": 2048,
                                    "mimeType": "image/png",
                                }
                            ],
                        }
                    ]
                },
            )
        body = json.loads(request.content)
        assert body["partnerMessageId"] == "pm-1"
        return httpx.Response(
            200, json={"messageId": "m-9", "partnerMessageId": "pm-1"}
        )

    client = _client(handler)
    chats = await client.list_chats("S")
    assert chats.chats[0].chat_id == "C"
    chat = await client.get_chat("S", "C")
    assert chat.description == "Заказ №5"
    msgs = await client.list_messages("S", "C", limit=50)
    assert msgs.messages[0].files[0].mime_type == "image/png"
    sent = await client.send_message(
        "S", "C", SendMessageRequest(partner_message_id="pm-1", text="ok")
    )
    assert sent.message_id == "m-9"


async def test_chat_files():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.headers["content-type"] == "application/octet-stream"
            assert request.headers["x-content-file-name"] == "doc.pdf"
            assert request.headers["x-content-file-type"] == "application/pdf"
            assert request.content == b"BYTES"
            return httpx.Response(200, json={"fileId": "cf-1"})
        assert request.url.path.endswith("/files/cf-1")
        return httpx.Response(200, content=b"BYTES")

    client = _client(handler)
    up = await client.upload_chat_file(
        "S", "C", b"BYTES", file_name="doc.pdf", file_type="application/pdf"
    )
    assert up.file_id == "cf-1"
    content = await client.download_chat_file("S", "C", "cf-1")
    assert content == b"BYTES"


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError):
        await client.list_chats("S")


def test_sync_client():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chats"):
            return httpx.Response(200, json={"chats": []})
        if request.url.path.endswith("/files/f"):
            return httpx.Response(200, content=b"X")
        return httpx.Response(500, text="boom")

    client = SyncClient(token="T", transport=_transport(handler, sync=True))
    assert client.list_chats("S").chats == []
    assert client.download_chat_file("S", "C", "f") == b"X"
    with pytest.raises(TBankAPIError):
        client.get_chat("S", "C")
    client.close()


def _surface_handler(request: httpx.Request) -> httpx.Response:
    p, m = request.url.path, request.method
    if p.endswith("/chats"):
        return httpx.Response(200, json={"chats": []})
    if p.endswith("/messages") and m == "GET":
        return httpx.Response(200, json={"messages": []})
    if p.endswith("/messages"):
        return httpx.Response(200, json={"messageId": "m", "partnerMessageId": "pm"})
    if p.endswith("/files") and m == "POST":
        return httpx.Response(200, json={"fileId": "cf"})
    if "/files/" in p:
        return httpx.Response(200, content=b"X")
    return httpx.Response(
        200, json={"chatId": "C", "createdAt": "2026-01-01T00:00:00+03:00"}
    )


def test_sync_full_surface():
    client = SyncClient(token="T", transport=_transport(_surface_handler, sync=True))
    assert client.list_chats("S").chats == []
    assert client.get_chat("S", "C").chat_id == "C"
    assert client.list_messages("S", "C", message_id_from="m0").messages == []
    assert (
        client.send_message(
            "S", "C", SendMessageRequest(partner_message_id="pm", text="ok")
        ).message_id
        == "m"
    )
    assert (
        client.upload_chat_file(
            "S", "C", b"X", file_name="f", file_type="application/pdf"
        ).file_id
        == "cf"
    )
    assert client.download_chat_file("S", "C", "cf") == b"X"
    client.close()
