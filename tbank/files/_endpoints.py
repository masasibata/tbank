"""Путь и заголовки файлового хранилища (общие для sync- и aio-клиентов)."""

from __future__ import annotations

from typing import Dict, Optional

FILES = "/api/v1/files"


def _bool(value: bool) -> str:
    return "true" if value else "false"


def download_headers(document_type: str, base64_encoded: bool) -> Dict[str, str]:
    return {
        "X-Document-Type": document_type,
        "X-Base64-Encoded": _bool(base64_encoded),
    }


def upload_headers(
    document_type: str,
    base64_encoded: bool,
    business_type: Optional[str],
    file_name: Optional[str],
    ttl: Optional[str],
) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Content-Type": "application/octet-stream",
        **download_headers(document_type, base64_encoded),
    }
    if business_type is not None:
        headers["X-Document-Business-Type"] = business_type
    if file_name is not None:
        headers["X-File-Name"] = file_name
    if ttl is not None:
        headers["X-TTL"] = ttl
    return headers
