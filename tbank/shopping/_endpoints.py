"""Пути чатов шопинга (общие для sync- и aio-клиентов)."""

from __future__ import annotations

SHOPS = "/api/v1/shopping/shops"


def chats_path(shop_id: str) -> str:
    return f"{SHOPS}/{shop_id}/chats"


def chat_path(shop_id: str, chat_id: str) -> str:
    return f"{SHOPS}/{shop_id}/chats/{chat_id}"


def messages_path(shop_id: str, chat_id: str) -> str:
    return f"{chat_path(shop_id, chat_id)}/messages"


def files_path(shop_id: str, chat_id: str) -> str:
    return f"{chat_path(shop_id, chat_id)}/files"


def file_path(shop_id: str, chat_id: str, file_id: str) -> str:
    return f"{files_path(shop_id, chat_id)}/{file_id}"
