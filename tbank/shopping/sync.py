from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.shopping.errors import error_from_shopping_response
from tbank.shopping.models import (
    Chat,
    ChatFileUploadResult,
    ChatList,
    MessageList,
    SendMessageRequest,
    SendMessageResult,
)

SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_SHOPS = "/api/v1/shopping/shops"


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
        cert: Optional[Any] = None,
        verify: Any = True,
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
        response = self._transport.request("GET", f"{_SHOPS}/{shop_id}/chats")
        self._raise_for_http(response)
        return ChatList.model_validate(self._parse_body(response))

    def get_chat(self, shop_id: str, chat_id: str) -> Chat:
        """Карточка чата."""
        response = self._transport.request("GET", f"{_SHOPS}/{shop_id}/chats/{chat_id}")
        self._raise_for_http(response)
        return Chat.model_validate(self._parse_body(response))

    def list_messages(
        self,
        shop_id: str,
        chat_id: str,
        *,
        limit: Optional[int] = None,
        message_id_from: Optional[str] = None,
    ) -> MessageList:
        """Сообщения чата."""
        response = self._transport.request(
            "GET",
            f"{_SHOPS}/{shop_id}/chats/{chat_id}/messages",
            params=_params(limit=limit, messageIdFrom=message_id_from),
        )
        self._raise_for_http(response)
        return MessageList.model_validate(self._parse_body(response))

    def send_message(
        self, shop_id: str, chat_id: str, request: SendMessageRequest
    ) -> SendMessageResult:
        """Отправить сообщение в чат."""
        response = self._transport.request(
            "POST",
            f"{_SHOPS}/{shop_id}/chats/{chat_id}/messages",
            json=request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        self._raise_for_http(response)
        return SendMessageResult.model_validate(self._parse_body(response))

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
            f"{_SHOPS}/{shop_id}/chats/{chat_id}/files",
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
            "GET", f"{_SHOPS}/{shop_id}/chats/{chat_id}/files/{file_id}"
        )
        self._raise_for_http(response)
        return response.content


def _params(**kwargs: Any) -> Dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}
