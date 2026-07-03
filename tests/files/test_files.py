import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.files.aio import PROD_URL, FilesClient
from tbank.files.sync import FilesClient as SyncClient


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=PROD_URL, client=client, auth=BearerAuth("T"))


def _client(handler):
    return FilesClient(token="T", transport=_transport(handler))


async def test_upload_file():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        assert request.url.path == "/openapi/api/v1/files"
        assert request.headers["content-type"] == "application/octet-stream"
        assert request.headers["X-Document-Type"] == "ACT"
        assert request.headers["X-Base64-Encoded"] == "false"
        assert request.headers["X-File-Name"] == "act.pdf"
        assert request.headers["X-TTL"] == "3600"
        assert request.content == b"PDFBYTES"
        return httpx.Response(200, json={"fileId": "f-1"})

    result = await _client(handler).upload_file(
        b"PDFBYTES", document_type="ACT", file_name="act.pdf", ttl="3600"
    )
    assert result.file_id == "f-1"


async def test_download_file():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("id") == "f-1"
        assert request.headers["X-Document-Type"] == "ACT"
        assert request.headers["X-Base64-Encoded"] == "true"
        return httpx.Response(200, content=b"PDFBYTES")

    content = await _client(handler).download_file(
        "f-1", document_type="ACT", base64_encoded=True
    )
    assert content == b"PDFBYTES"


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError):
        await client.download_file("f-1", document_type="ACT")


def test_sync_client():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.headers["X-Document-Business-Type"] == "INVOICE"
            assert request.headers["X-File-Name"] == "f.pdf"
            assert request.headers["X-TTL"] == "60"
            return httpx.Response(200, json={"fileId": "f-9"})
        return httpx.Response(200, content=b"OK")

    client = SyncClient(token="T", transport=_transport(handler, sync=True))
    assert (
        client.upload_file(
            b"X",
            document_type="ACT",
            business_type="INVOICE",
            file_name="f.pdf",
            ttl="60",
        ).file_id
        == "f-9"
    )
    assert client.download_file("f-1", document_type="ACT") == b"OK"
    client.close()


def test_sync_error():
    client = SyncClient(
        token="T",
        transport=_transport(lambda r: httpx.Response(500, text="boom"), sync=True),
    )
    with pytest.raises(TBankAPIError):
        client.download_file("f-1", document_type="ACT")
    client.close()
