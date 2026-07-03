"""Пути, парсеры и тело для подписи внутренних писем (общие для sync- и
aio-клиентов)."""

from __future__ import annotations

import json
from typing import List

from pydantic import BaseModel, TypeAdapter

from tbank.core.client import dump_model
from tbank.mails.models import Mail

BASE = "/api/internal/v1/mails"
INCOMING = f"{BASE}/incoming"
READ = f"{BASE}/read"
UNREAD = f"{BASE}/unread"

UNREAD_LIST: TypeAdapter[List[Mail]] = TypeAdapter(List[Mail])


def body_bytes(request: BaseModel) -> bytes:
    """Канонические байты тела: подписываются и отправляются как есть."""
    return json.dumps(
        dump_model(request), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
