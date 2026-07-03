from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ShoppingModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class Chat(ShoppingModel):
    chat_id: str
    created_at: datetime
    description: Optional[str] = None


class ChatList(ShoppingModel):
    chats: List[Chat] = Field(default_factory=list)


class MessageFile(ShoppingModel):
    id: str
    name: str
    size: int
    mime_type: str


class MessageAuthor(ShoppingModel):
    name: str


class ChatMessage(ShoppingModel):
    message_id: str
    author: MessageAuthor
    created_at: datetime
    message: Optional[str] = None
    files: Optional[List[MessageFile]] = None


class MessageList(ShoppingModel):
    messages: List[ChatMessage] = Field(default_factory=list)


class SendMessageRequest(ShoppingModel):
    """Сообщение в чат. Требуется `text` либо `file_id`. `partner_message_id` —
    ключ идемпотентности на стороне партнёра."""

    partner_message_id: str
    text: Optional[str] = None
    file_id: Optional[str] = None


class SendMessageResult(ShoppingModel):
    message_id: str
    partner_message_id: str


class ChatFileUploadResult(ShoppingModel):
    file_id: str
