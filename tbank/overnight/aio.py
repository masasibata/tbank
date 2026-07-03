from __future__ import annotations

from typing import Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport, CertTypes, VerifyTypes
from tbank.core.urls import SANDBOX_SECURED_URL, SECURED_URL
from tbank.overnight._endpoints import INFO as _INFO
from tbank.overnight._endpoints import REPLENISH as _REPLENISH
from tbank.overnight.errors import error_from_overnight_response
from tbank.overnight.models import OvernightInfo


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
        cert: Optional[CertTypes] = None,
        verify: VerifyTypes = True,
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
        return await self._send(
            "POST", _INFO, OvernightInfo, params={"agreementNumber": agreement_number}
        )

    async def replenish_overnight(self, agreement_number: str, amount: str) -> None:
        """Пополнить счёт овернайт на указанную сумму."""
        await self._send(
            "POST",
            _REPLENISH,
            params={"agreementNumber": agreement_number, "amount": amount},
        )
