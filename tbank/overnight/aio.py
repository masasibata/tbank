from __future__ import annotations

from typing import Any, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport
from tbank.overnight.errors import error_from_overnight_response
from tbank.overnight.models import OvernightInfo

SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_INFO = "/api/v1/overnight/info"
_REPLENISH = "/api/v1/overnight/replenish"


class OvernightClient(BaseAsyncClient):
    """Асинхронный клиент овернайта: сводка по счёту и пополнение.

    Домен работает на secured-хосте и требует **mTLS-сертификата** (`cert`).
    Суммы T-API отдаёт строками — модели сохраняют их как есть.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        sandbox: bool = False,
        cert: Optional[Any] = None,
        verify: Any = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[AsyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_SECURED_URL if sandbox else SECURED_URL)
        transport = transport or AsyncTransport(
            base_url=resolved,
            auth=BearerAuth(token),
            cert=cert,
            verify=verify,
            retry=retry,
        )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_overnight_response(response)

    async def get_overnight_info(self, agreement_number: str) -> OvernightInfo:
        """Сводка по счёту овернайт: суммы, ставка, автоплатёж, текущая сделка."""
        response = await self._transport.request(
            "POST", _INFO, params={"agreementNumber": agreement_number}
        )
        self._raise_for_http(response)
        return OvernightInfo.model_validate(self._parse_body(response))

    async def replenish_overnight(self, agreement_number: str, amount: str) -> None:
        """Пополнить счёт овернайт на указанную сумму."""
        response = await self._transport.request(
            "POST",
            _REPLENISH,
            params={"agreementNumber": agreement_number, "amount": amount},
        )
        self._raise_for_http(response)
