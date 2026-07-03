from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.client import ensure_idempotency_key as _idem
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.core.urls import PROD_URL, SANDBOX_URL
from tbank.delivery._endpoints import DOCUMENTS as _DOCUMENTS
from tbank.delivery._endpoints import MEETINGS as _MEETINGS
from tbank.delivery._endpoints import TASKS as _TASKS
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


class DeliveryClient(BaseSyncClient):
    """Синхронный клиент партнёрской доставки: задания, встречи и интервалы,
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
        transport: Optional[SyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_URL if sandbox else PROD_URL)
        transport = transport or SyncTransport(
            base_url=resolved, auth=BearerAuth(token), retry=retry
        )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_delivery_response(response)

    # --- Задания ---

    def create_task(
        self, request: CreateTaskRequest, *, idempotency_key: Optional[str] = None
    ) -> CreateTaskResult:
        """Создать задание на доставку/встречу."""
        return self._send(
            "POST",
            _TASKS,
            CreateTaskResult,
            body=request,
            idempotency_key=_idem(idempotency_key),
        )

    def get_task(self, task_id: str) -> DeliveryTask:
        """Карточка задания."""
        return self._get(f"{_TASKS}/{task_id}", DeliveryTask)

    def update_task(self, task_id: str, request: UpdateTaskRequest) -> None:
        """Обновить задание."""
        self._send("PUT", f"{_TASKS}/{task_id}", body=request)

    def cancel_task(self, task_id: str, request: CancelTaskRequest) -> None:
        """Отменить задание."""
        self._send("POST", f"{_TASKS}/{task_id}/cancel", body=request)

    # --- Встречи ---

    def get_intervals(self, request: GetIntervalsRequest) -> GetIntervalsResult:
        """Доступные интервалы встречи по адресу."""
        return self._send(
            "POST", f"{_MEETINGS}/intervals", GetIntervalsResult, body=request
        )

    def create_meeting(self, request: CreateMeetingRequest) -> CreateMeetingResult:
        """Назначить встречу на выбранный интервал."""
        return self._send("POST", _MEETINGS, CreateMeetingResult, body=request)

    # --- Документы ---

    def upload_document(
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
        response = self._transport.request(
            "POST", _DOCUMENTS, data=data, files={"content": (filename, content)}
        )
        self._raise_for_http(response)
        return UploadDocumentResult.model_validate(self._parse_body(response))

    def download_document(self, document_id: str) -> bytes:
        """Скачать документ задания (бинарное содержимое)."""
        response = self._transport.request("GET", f"{_DOCUMENTS}/{document_id}")
        self._raise_for_http(response)
        return response.content
