from __future__ import annotations

from typing import Any, Dict, Optional

from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.errors import raise_for_acquiring_result
from tbank.acquiring.models import (
    CancelRequest,
    CancelResponse,
    ConfirmRequest,
    ConfirmResponse,
    GetStateRequest,
    GetStateResponse,
    InitRequest,
    InitResponse,
)
from tbank.core.client import BaseAsyncClient
from tbank.core.endpoint import Endpoint
from tbank.core.models import Kopecks
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport

BASE_URL = "https://securepay.tinkoff.ru/v2"

_INIT = Endpoint("POST", "/Init", InitResponse, InitRequest)
_GET_STATE = Endpoint("POST", "/GetState", GetStateResponse, GetStateRequest)
_CONFIRM = Endpoint("POST", "/Confirm", ConfirmResponse, ConfirmRequest)
_CANCEL = Endpoint("POST", "/Cancel", CancelResponse, CancelRequest)


class AcquiringClient(BaseAsyncClient):
    """Асинхронный клиент интернет-эквайринга Т-Банка (redirect-поток)."""

    def __init__(
        self,
        terminal_key: str,
        password: str,
        *,
        base_url: str = BASE_URL,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[AsyncTransport] = None,
    ) -> None:
        transport = transport or AsyncTransport(
            base_url=base_url,
            auth=TokenSignatureAuth(terminal_key, password),
            retry=retry,
        )
        super().__init__(transport)

    def _check_error(self, data: Dict[str, Any]) -> None:
        raise_for_acquiring_result(data)

    async def init(self, request: InitRequest) -> InitResponse:
        return await self._call(_INIT, request)

    async def get_state(self, payment_id: str) -> GetStateResponse:
        return await self._call(_GET_STATE, GetStateRequest(payment_id=payment_id))

    async def confirm(
        self, payment_id: str, amount: Optional[Kopecks] = None
    ) -> ConfirmResponse:
        return await self._call(
            _CONFIRM, ConfirmRequest(payment_id=payment_id, amount=amount)
        )

    async def cancel(
        self, payment_id: str, amount: Optional[Kopecks] = None
    ) -> CancelResponse:
        return await self._call(
            _CANCEL, CancelRequest(payment_id=payment_id, amount=amount)
        )
