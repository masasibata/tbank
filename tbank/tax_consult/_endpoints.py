"""Пути API налоговых консультаций (общие для sync- и aio-клиентов)."""

from __future__ import annotations

_BASE = "/api/v1/consult/requests"

COMMENT = f"{_BASE}/comment"
CHAT = f"{COMMENT}/chat"
CHAT_SEND = f"{CHAT}/send"
ATTACHMENTS = f"{_BASE}/attachments"
ATTACHMENTS_UPLOAD = f"{ATTACHMENTS}/upload"


def workflow_path(action: str) -> str:
    return f"{COMMENT}/workflow/{action}"
