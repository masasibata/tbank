from __future__ import annotations

from typing import Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.client import page_params as _page
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import CertTypes, SyncTransport, VerifyTypes
from tbank.core.urls import SANDBOX_SECURED_URL, SECURED_URL
from tbank.shopping import _endpoints
from tbank.shopping.errors import error_from_shopping_response
from tbank.shopping.models import (
    Chat,
    ChatFileUploadResult,
    ChatList,
    MessageList,
    SendMessageRequest,
    SendMessageResult,
)


class ShoppingClient(BaseSyncClient):
    """Синхронный клиент шопинга (чаты магазина): чаты, сообщения и файлы.

    Домен работает на secured-хосте (**mTLS**, `cert`) по **Bearer**-токену.
    Провод — `camelCase`.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        sandbox: bool = False,
        cert: Optional[CertTypes] = None,
        verify: VerifyTypes = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[SyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_SECURED_URL if sandbox else SECURED_URL)
        transport = transport or SyncTransport(
            base_url=resolved,
            auth=BearerAuth(token),
            cert=cert,
            verify=verify,
            retry=retry,
        )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_shopping_response(response)

    def list_chats(self, shop_id: str) -> ChatList:
        """Список чатов магазина."""
        return self._get(_endpoints.chats_path(shop_id), ChatList)

    def get_chat(self, shop_id: str, chat_id: str) -> Chat:
        """Карточка чата."""
        return self._get(_endpoints.chat_path(shop_id, chat_id), Chat)

    def list_messages(
        self,
        shop_id: str,
        chat_id: str,
        *,
        limit: Optional[int] = None,
        message_id_from: Optional[str] = None,
    ) -> MessageList:
        """Сообщения чата."""
        return self._get(
            _endpoints.messages_path(shop_id, chat_id),
            MessageList,
            params=_page(limit=limit, messageIdFrom=message_id_from),
        )

    def send_message(
        self, shop_id: str, chat_id: str, request: SendMessageRequest
    ) -> SendMessageResult:
        """Отправить сообщение в чат."""
        return self._send(
            "POST",
            _endpoints.messages_path(shop_id, chat_id),
            SendMessageResult,
            body=request,
        )

    def upload_chat_file(
        self,
        shop_id: str,
        chat_id: str,
        content: bytes,
        *,
        file_name: str,
        file_type: str,
    ) -> ChatFileUploadResult:
        """Загрузить файл в чат (octet-stream). Возвращает идентификатор файла."""
        response = self._transport.request(
            "POST",
            _endpoints.files_path(shop_id, chat_id),
            content=content,
            headers={
                "Content-Type": "application/octet-stream",
                "x-content-file-name": file_name,
                "x-content-file-type": file_type,
            },
        )
        self._raise_for_http(response)
        return ChatFileUploadResult.model_validate(self._parse_body(response))

    def download_chat_file(self, shop_id: str, chat_id: str, file_id: str) -> bytes:
        """Скачать файл из чата (бинарное содержимое)."""
        response = self._transport.request(
            "GET", _endpoints.file_path(shop_id, chat_id, file_id)
        )
        self._raise_for_http(response)
        return response.content
