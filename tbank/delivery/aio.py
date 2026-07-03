from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport
from tbank.delivery.errors import error_from_delivery_response
from tbank.delivery.models import (
    CancelTaskRequest,
    CreateMeetingRequest,
    CreateMeetingResult,
    CreateTaskRequest,
    CreateTaskResult,
    DeliveryTask,
    GetIntervalsRequest,
    GetIntervalsResult,
    UpdateTaskRequest,
    UploadDocumentResult,
)

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"

_TASKS = "/api/v1/delivery/tasks"
_MEETINGS = "/api/v1/delivery/meetings"
_DOCUMENTS = "/api/v1/delivery/documents"


class DeliveryClient(BaseAsyncClient):
    """Асинхронный клиент партнёрской доставки: задания, встречи и интервалы,
    документы (загрузка и скачивание).

    Работает на обычном хосте по **Bearer**-токену. Провод — `camelCase`.
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
        return error_from_delivery_response(response)

    # --- Задания ---

    async def create_task(
        self, request: CreateTaskRequest, *, idempotency_key: Optional[str] = None
    ) -> CreateTaskResult:
        """Создать задание на доставку/встречу."""
        response = await self._transport.request(
            "POST",
            _TASKS,
            json=_dump(request),
            headers={"Idempotency-Key": idempotency_key or str(uuid.uuid4())},
        )
        self._raise_for_http(response)
        return CreateTaskResult.model_validate(self._parse_body(response))

    async def get_task(self, task_id: str) -> DeliveryTask:
        """Карточка задания."""
        response = await self._transport.request("GET", f"{_TASKS}/{task_id}")
        self._raise_for_http(response)
        return DeliveryTask.model_validate(self._parse_body(response))

    async def update_task(self, task_id: str, request: UpdateTaskRequest) -> None:
        """Обновить задание."""
        response = await self._transport.request(
            "PUT", f"{_TASKS}/{task_id}", json=_dump(request)
        )
        self._raise_for_http(response)

    async def cancel_task(self, task_id: str, request: CancelTaskRequest) -> None:
        """Отменить задание."""
        response = await self._transport.request(
            "POST", f"{_TASKS}/{task_id}/cancel", json=_dump(request)
        )
        self._raise_for_http(response)

    # --- Встречи ---

    async def get_intervals(self, request: GetIntervalsRequest) -> GetIntervalsResult:
        """Доступные интервалы встречи по адресу."""
        response = await self._transport.request(
            "POST", f"{_MEETINGS}/intervals", json=_dump(request)
        )
        self._raise_for_http(response)
        return GetIntervalsResult.model_validate(self._parse_body(response))

    async def create_meeting(
        self, request: CreateMeetingRequest
    ) -> CreateMeetingResult:
        """Назначить встречу на выбранный интервал."""
        response = await self._transport.request("POST", _MEETINGS, json=_dump(request))
        self._raise_for_http(response)
        return CreateMeetingResult.model_validate(self._parse_body(response))

    # --- Документы ---

    async def upload_document(
        self,
        task_id: str,
        document_type: str,
        content: bytes,
        *,
        prev_doc_id: Optional[str] = None,
        filename: str = "document",
    ) -> UploadDocumentResult:
        """Загрузить документ и связать с заданием (multipart)."""
        data: Dict[str, Any] = {"taskId": task_id, "type": document_type}
        if prev_doc_id is not None:
            data["prevDocId"] = prev_doc_id
        response = await self._transport.request(
            "POST", _DOCUMENTS, data=data, files={"content": (filename, content)}
        )
        self._raise_for_http(response)
        return UploadDocumentResult.model_validate(self._parse_body(response))

    async def download_document(self, document_id: str) -> bytes:
        """Скачать документ задания (бинарное содержимое)."""
        response = await self._transport.request("GET", f"{_DOCUMENTS}/{document_id}")
        self._raise_for_http(response)
        return response.content


def _dump(request: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = request.model_dump(
        by_alias=True, exclude_none=True, mode="json"
    )
    return result
