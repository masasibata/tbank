from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, Type, TypeVar

from tbank.core.models import TBankModel

TReq = TypeVar("TReq", bound=TBankModel)
TResp = TypeVar("TResp", bound=TBankModel)


@dataclass(frozen=True)
class Endpoint(Generic[TReq, TResp]):
    method: str
    path: str
    response_model: Type[TResp]
    request_model: Optional[Type[TReq]] = None
