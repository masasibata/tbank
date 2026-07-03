from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, Type, TypeVar

from pydantic import BaseModel

TResp = TypeVar("TResp", bound=BaseModel)


@dataclass(frozen=True)
class Endpoint(Generic[TResp]):
    """Декларация вызова API: метод, путь и модели запроса/ответа.

    `request_model` позволяет передавать в `_call` словарь — он будет
    провалидирован и приведён к модели. `secured=True` направляет вызов
    на secured-хост (mTLS)."""

    method: str
    path: str
    response_model: Type[TResp]
    request_model: Optional[Type[BaseModel]] = None
    secured: bool = False
