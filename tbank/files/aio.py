from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport
from tbank.files.errors import error_from_files_response
from tbank.files.models import FileUploadResult

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"

_FILES = "/api/v1/files"


class FilesClient(BaseAsyncClient):
    """Асинхронный клиент файлового хранилища: загрузка и скачивание файлов.

    Работает на обычном хосте по **Bearer**-токену. Тело файла передаётся как
    `application/octet-stream`; скачивание возвращает «сырые» байты.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        sandbox: bool = False,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[AsyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_URL if sandbox else PROD_URL)
        transport = transport or AsyncTransport(
            base_url=resolved, auth=BearerAuth(token), retry=retry
        )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_files_response(response)

    async def upload_file(
        self,
        content: bytes,
        *,
        document_type: str,
        base64_encoded: bool = False,
        business_type: Optional[str] = None,
        file_name: Optional[str] = None,
        ttl: Optional[str] = None,
    ) -> FileUploadResult:
        """Загрузить файл. Возвращает его идентификатор."""
        headers = _upload_headers(
            document_type, base64_encoded, business_type, file_name, ttl
        )
        response = await self._transport.request(
            "POST", _FILES, content=content, headers=headers
        )
        self._raise_for_http(response)
        return FileUploadResult.model_validate(self._parse_body(response))

    async def download_file(
        self, file_id: str, *, document_type: str, base64_encoded: bool = False
    ) -> bytes:
        """Скачать файл по идентификатору (бинарное содержимое)."""
        response = await self._transport.request(
            "GET",
            _FILES,
            params={"id": file_id},
            headers={
                "X-Document-Type": document_type,
                "X-Base64-Encoded": _bool(base64_encoded),
            },
        )
        self._raise_for_http(response)
        return response.content


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _upload_headers(
    document_type: str,
    base64_encoded: bool,
    business_type: Optional[str],
    file_name: Optional[str],
    ttl: Optional[str],
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {
        "Content-Type": "application/octet-stream",
        "X-Document-Type": document_type,
        "X-Base64-Encoded": _bool(base64_encoded),
    }
    if business_type is not None:
        headers["X-Document-Business-Type"] = business_type
    if file_name is not None:
        headers["X-File-Name"] = file_name
    if ttl is not None:
        headers["X-TTL"] = ttl
    return headers
