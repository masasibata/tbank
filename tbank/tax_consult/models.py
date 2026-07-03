from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from tbank.tax_consult.enums import ChatAuthorType, RequestStatus, RequestType


class TaxConsultModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class ConsultRequest(TaxConsultModel):
    """Карточка заявки на консультацию."""

    client_id: str
    client_full_name: str
    request_type: RequestType
    status: RequestStatus
    has_unread_messages: bool
    cas_version: int
    created_at: datetime


class WorkflowState(TaxConsultModel):
    """Состояние заявки после перехода воркфлоу."""

    status: RequestStatus
    cas_version: int


class ChatAttachment(TaxConsultModel):
    id: str
    name: str
    mime: str
    size: int
    created_at: datetime


class ChatMessage(TaxConsultModel):
    id: str
    author_type: ChatAuthorType
    created_at: datetime
    text: Optional[str] = None
    attachments: Optional[List[ChatAttachment]] = None


class ChatMeta(TaxConsultModel):
    offset: int
    count: int
    total: int


class ChatPage(TaxConsultModel):
    """Страница сообщений чата заявки."""

    meta: ChatMeta
    values: List[ChatMessage] = Field(default_factory=list)


class SendMessageRequest(TaxConsultModel):
    text: Optional[str] = None
    attachments: Optional[List[str]] = None


class UploadAttachmentResult(TaxConsultModel):
    attachment_id: str
