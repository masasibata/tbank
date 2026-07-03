from __future__ import annotations

from typing import Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport, CertTypes, VerifyTypes
from tbank.core.urls import SANDBOX_SECURED_URL, SECURED_URL
from tbank.deposit import _endpoints
from tbank.deposit.errors import error_from_deposit_response
from tbank.deposit.models import (
    DepositAccountDetails,
    OpenDepositRequest,
    OpenDepositResult,
    ReplenishDepositRequest,
)


class DepositClient(BaseAsyncClient):
    """Асинхронный клиент депозитов: карточка счёта, открытие и пополнение.

    Домен работает на secured-хосте и требует **mTLS-сертификата** (`cert`).
    Суммы — `Decimal` в валюте депозита. Провод — `camelCase`.
    """

    decimal_body = True

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
        return error_from_deposit_response(response)

    async def get_deposit_details(self, agreement_number: str) -> DepositAccountDetails:
        """Карточка депозита: баланс, договор, ставка, условия."""
        return await self._get(
            _endpoints.DETAILS,
            DepositAccountDetails,
            params={"agreementNumber": agreement_number},
        )

    async def open_deposit(self, request: OpenDepositRequest) -> OpenDepositResult:
        """Открыть депозит. Возвращает идентификаторы процесса и заявки."""
        return await self._send(
            "POST", _endpoints.OPEN, OpenDepositResult, body=request
        )

    async def replenish_deposit(self, request: ReplenishDepositRequest) -> None:
        """Пополнить депозит с указанного счёта-источника."""
        await self._send("POST", _endpoints.REPLENISH, body=request)
