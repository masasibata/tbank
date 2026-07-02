from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, Type, TypeVar

from pydantic import BaseModel

TResp = TypeVar("TResp", bound=BaseModel)


@dataclass(frozen=True)
class Endpoint(Generic[TResp]):
    method: str
    path: str
    response_model: Type[TResp]
    request_model: Optional[Type[BaseModel]] = None
    secured: bool = False  # True → идёт на secured-хост (mTLS)
