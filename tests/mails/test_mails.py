import base64
import hashlib
import hmac
import json

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError
from tbank.core.signing import HttpSignature
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.mails.aio import SECURED_URL, MailsClient, MailSignatureRequiredError
from tbank.mails.models import IncomingMailRequest, MarkReadRequest
from tbank.mails.sync import MailsClient as SyncClient

_SIG = HttpSignature("key-1", "topsecret")


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=SECURED_URL, client=client, auth=BearerAuth("T"))


def _client(handler, *, signature=_SIG):
    return MailsClient(token="T", signature=signature, transport=_transport(handler))


async def test_push_incoming_signed():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "secured-openapi.tbank.ru"
        assert request.url.path == "/api/internal/v1/mails/incoming"
        assert request.headers["content-type"] == "application/json"
        assert request.headers.get("Signature", "").startswith("Signature keyId=")
        expected = base64.b64encode(
            hmac.new(b"topsecret", request.content, hashlib.sha256).digest()
        ).decode()
        assert request.headers["data"] == expected
        body = json.loads(request.content)
        assert body["externalId"] == "ext-1"
        assert body["files"] == ["tecm-1"]
        return httpx.Response(200, json={"id": "mail-1"})

    result = await _client(handler).push_incoming_mail(
        IncomingMailRequest(
            external_id="ext-1",
            theme_code="TAX",
            theme="Вопрос",
            created_at="2026-06-01T10:00:00Z",
            files=["tecm-1"],
        )
    )
    assert result.id == "mail-1"


async def test_push_without_signature_raises():
    client = _client(lambda r: httpx.Response(200, json={}), signature=None)
    with pytest.raises(MailSignatureRequiredError):
        await client.push_incoming_mail(
            IncomingMailRequest(
                external_id="e",
                theme_code="T",
                theme="t",
                created_at="2026-06-01T10:00:00Z",
                text="hi",
            )
        )


async def test_mark_read_and_unread():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/read"):
            assert json.loads(request.content)["messagesIds"] == ["m-1", "m-2"]
            return httpx.Response(200, json={})
        return httpx.Response(
            200,
            json=[
                {
                    "id": "mail-1",
                    "number": 5,
                    "companyId": "co-1",
                    "isFromBank": True,
                    "theme": "Вопрос",
                    "themeCode": "TAX",
                    "status": "NEW",
                    "updatedAt": "2026-06-01T12:00:00Z",
                    "messages": [
                        {
                            "id": "msg-1",
                            "mailId": "mail-1",
                            "isFromBank": True,
                            "isUnread": True,
                            "createdAt": "2026-06-01T12:00:00Z",
                            "text": "Ответ",
                        }
                    ],
                }
            ],
        )

    client = _client(handler)
    assert await client.mark_read(MarkReadRequest(messages_ids=["m-1", "m-2"])) is None
    unread = await client.list_unread()
    assert unread[0].number == 5
    assert unread[0].messages[0].text == "Ответ"


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError):
        await client.list_unread()


def test_sync_client():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/incoming"):
            return httpx.Response(200, json={"id": "mail-9"})
        if request.url.path.endswith("/unread"):
            return httpx.Response(200, json=[])
        return httpx.Response(500, text="boom")

    client = SyncClient(
        token="T", signature=_SIG, transport=_transport(handler, sync=True)
    )
    result = client.push_incoming_mail(
        IncomingMailRequest(
            external_id="e",
            theme_code="T",
            theme="t",
            created_at="2026-06-01T10:00:00Z",
            text="hi",
        )
    )
    assert result.id == "mail-9"
    assert client.list_unread() == []
    with pytest.raises(TBankAPIError):
        client.mark_read(MarkReadRequest(messages_ids=["x"]))
    client.close()

    nosig = SyncClient(token="T", transport=_transport(handler, sync=True))
    with pytest.raises(MailSignatureRequiredError):
        nosig.push_incoming_mail(
            IncomingMailRequest(
                external_id="e",
                theme_code="T",
                theme="t",
                created_at="2026-06-01T10:00:00Z",
                text="hi",
            )
        )
    nosig.close()
