"""Пути и тело для подписи валютного контроля (общие для sync- и aio-клиентов)."""

from __future__ import annotations

import json

from pydantic import BaseModel

from tbank.core.client import dump_model

REGISTRATION = "/api/v1/currency/contracts/openapi/registration"
AMENDMENT = "/api/v1/currency/contracts/openapi/amendment"
DEREGISTRATION = "/api/v1/currency/contracts/openapi/deregistration"
STATUS = "/api/v2/currency/contracts/applications/openapi/status"


def body_bytes(request: BaseModel) -> bytes:
    """Канонические байты тела: подписываются и отправляются как есть."""
    return json.dumps(
        dump_model(request), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
