from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class MailModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class IncomingMailRequest(MailModel):
    """Входящее письмо (H2H). Требуется `text` либо `files`."""

    external_id: str
    theme_code: str
    theme: str
    created_at: datetime
    text: Optional[str] = None
    files: Optional[List[str]] = None


class IncomingMailResult(MailModel):
    id: str


class MarkReadRequest(MailModel):
    messages_ids: List[str]


class MailMessage(MailModel):
    id: str
    mail_id: str
    is_from_bank: bool
    is_unread: bool
    created_at: datetime
    text: Optional[str] = None
    files: Optional[List[str]] = None


class Mail(MailModel):
    """Письмо со списком сообщений."""

    id: str
    number: int
    company_id: str
    is_from_bank: bool
    theme: str
    theme_code: str
    status: str
    updated_at: datetime
    messages: List[MailMessage] = Field(default_factory=list)
    external_id: Optional[str] = None
