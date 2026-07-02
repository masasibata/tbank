from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, Type, TypeVar

from pydantic import BaseModel

TReq = TypeVar("TReq", bound=BaseModel)
TResp = TypeVar("TResp", bound=BaseModel)


@dataclass(frozen=True)
class Endpoint(Generic[TReq, TResp]):
    method: str
    path: str
    response_model: Type[TResp]
    request_model: Optional[Type[TReq]] = None
    secured: bool = False  # True → идёт на secured-хост (mTLS)
