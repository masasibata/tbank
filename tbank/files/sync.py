from __future__ import annotations

from typing import Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.core.urls import PROD_URL, SANDBOX_URL
from tbank.files import _endpoints
from tbank.files.errors import error_from_files_response
from tbank.files.models import FileUploadResult


class FilesClient(BaseSyncClient):
    """Синхронный клиент файлового хранилища: загрузка и скачивание файлов.

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
        transport: Optional[SyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_URL if sandbox else PROD_URL)
        transport = transport or SyncTransport(
            base_url=resolved, auth=BearerAuth(token), retry=retry
        )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_files_response(response)

    def upload_file(
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
        headers = _endpoints.upload_headers(
            document_type, base64_encoded, business_type, file_name, ttl
        )
        response = self._transport.request(
            "POST", _endpoints.FILES, content=content, headers=headers
        )
        self._raise_for_http(response)
        return FileUploadResult.model_validate(self._parse_body(response))

    def download_file(
        self, file_id: str, *, document_type: str, base64_encoded: bool = False
    ) -> bytes:
        """Скачать файл по идентификатору (бинарное содержимое)."""
        response = self._transport.request(
            "GET",
            _endpoints.FILES,
            params={"id": file_id},
            headers=_endpoints.download_headers(document_type, base64_encoded),
        )
        self._raise_for_http(response)
        return response.content
