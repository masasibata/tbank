from __future__ import annotations

import uuid
from typing import Any, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport
from tbank.tax_consult.errors import error_from_tax_consult_response
from tbank.tax_consult.models import (
    ChatPage,
    ConsultRequest,
    SendMessageRequest,
    UploadAttachmentResult,
    WorkflowState,
)

SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_BASE = "/api/v1/consult/requests"
_COMMENT = f"{_BASE}/comment"
_WORKFLOW = f"{_COMMENT}/workflow"
_ATTACHMENTS = f"{_BASE}/attachments"


class TaxConsultClient(BaseAsyncClient):
    """Асинхронный клиент налоговых консультаций: карточка заявки, чат с менеджером,
    вложения и переходы воркфлоу заявки.

    Весь домен работает на secured-хосте и требует **mTLS-сертификата** (`cert`).
    Переходы воркфлоу используют оптимистичную блокировку: передайте `cas_version`
    из карточки заявки (уходит в заголовок `If-Match`). Провод — `camelCase`.
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
        transport: Optional[AsyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_SECURED_URL if sandbox else SECURED_URL)
        transport = transport or AsyncTransport(
            base_url=resolved,
            auth=BearerAuth(token),
            cert=cert,
            verify=verify,
            retry=retry,
        )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_tax_consult_response(response)

    # --- Заявка и чат ---

    async def get_request(self, tax_request_id: str) -> ConsultRequest:
        """Карточка заявки: тип, статус, версия, непрочитанные сообщения."""
        response = await self._transport.request(
            "GET", _COMMENT, params={"taxRequestId": tax_request_id}
        )
        self._raise_for_http(response)
        return ConsultRequest.model_validate(self._parse_body(response))

    async def get_chat(
        self, tax_request_id: str, *, limit: int, offset: int
    ) -> ChatPage:
        """Сообщения чата заявки (постранично)."""
        response = await self._transport.request(
            "GET",
            f"{_COMMENT}/chat",
            params={"taxRequestId": tax_request_id, "limit": limit, "offset": offset},
        )
        self._raise_for_http(response)
        return ChatPage.model_validate(self._parse_body(response))

    async def send_message(
        self, tax_request_id: str, request: SendMessageRequest
    ) -> None:
        """Отправить сообщение в чат заявки."""
        response = await self._transport.request(
            "POST",
            f"{_COMMENT}/chat/send",
            params={"taxRequestId": tax_request_id},
            json=request.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        self._raise_for_http(response)

    # --- Вложения ---

    async def download_attachment(
        self, tax_request_id: str, attachment_id: str
    ) -> bytes:
        """Скачать вложение заявки (бинарное содержимое)."""
        response = await self._transport.request(
            "GET",
            _ATTACHMENTS,
            params={"taxRequestId": tax_request_id, "attachmentId": attachment_id},
        )
        self._raise_for_http(response)
        return response.content

    async def upload_attachment(
        self,
        tax_request_id: str,
        content: bytes,
        *,
        file_name: str,
        file_type: str,
        idempotency_key: Optional[str] = None,
    ) -> UploadAttachmentResult:
        """Загрузить вложение к заявке (octet-stream)."""
        response = await self._transport.request(
            "POST",
            f"{_ATTACHMENTS}/upload",
            params={"taxRequestId": tax_request_id},
            content=content,
            headers={
                "Content-Type": "application/octet-stream",
                "X-Content-File-Name": file_name,
                "X-Content-File-Type": file_type,
                "X-Idempotency-Key": idempotency_key or str(uuid.uuid4()),
            },
        )
        self._raise_for_http(response)
        return UploadAttachmentResult.model_validate(self._parse_body(response))

    # --- Воркфлоу ---

    async def _workflow(
        self, action: str, tax_request_id: str, cas_version: int
    ) -> WorkflowState:
        response = await self._transport.request(
            "POST",
            f"{_WORKFLOW}/{action}",
            params={"taxRequestId": tax_request_id},
            headers={"If-Match": str(cas_version)},
        )
        self._raise_for_http(response)
        return WorkflowState.model_validate(self._parse_body(response))

    async def start_review(
        self, tax_request_id: str, cas_version: int
    ) -> WorkflowState:
        """Взять заявку на рассмотрение."""
        return await self._workflow("start-review", tax_request_id, cas_version)

    async def start_work(self, tax_request_id: str, cas_version: int) -> WorkflowState:
        """Начать работу по заявке."""
        return await self._workflow("start-work", tax_request_id, cas_version)

    async def request_clarification(
        self, tax_request_id: str, cas_version: int
    ) -> WorkflowState:
        """Запросить уточнение у клиента."""
        return await self._workflow("clarification", tax_request_id, cas_version)

    async def decline(self, tax_request_id: str, cas_version: int) -> WorkflowState:
        """Отклонить заявку."""
        return await self._workflow("decline", tax_request_id, cas_version)

    async def cancel(self, tax_request_id: str, cas_version: int) -> WorkflowState:
        """Отменить заявку."""
        return await self._workflow("cancel", tax_request_id, cas_version)

    async def set_pending_payment(
        self, tax_request_id: str, cas_version: int
    ) -> WorkflowState:
        """Перевести заявку в ожидание оплаты."""
        return await self._workflow("pending-payment", tax_request_id, cas_version)

    async def confirm_payment(
        self, tax_request_id: str, cas_version: int
    ) -> WorkflowState:
        """Подтвердить оплату заявки."""
        return await self._workflow("payment-done", tax_request_id, cas_version)

    async def mark_ready(self, tax_request_id: str, cas_version: int) -> WorkflowState:
        """Отметить заявку готовой (ответ предоставлен)."""
        return await self._workflow("ready", tax_request_id, cas_version)
