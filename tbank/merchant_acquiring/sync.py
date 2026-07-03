from __future__ import annotations

from typing import Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.core.urls import PROD_URL, SANDBOX_URL
from tbank.merchant_acquiring import _endpoints
from tbank.merchant_acquiring.errors import error_from_merchant_acquiring_response
from tbank.merchant_acquiring.models import OperationList, TerminalsPage


class MerchantAcquiringClient(BaseSyncClient):
    """Синхронный клиент торгового эквайринга: список терминалов и операции по ним.

    Работает на обычном хосте по **Bearer**-токену. Суммы — в копейках (`int`).
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        sandbox: bool = False,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[SyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_URL if sandbox else PROD_URL)
        transport = transport or SyncTransport(
            base_url=resolved, auth=BearerAuth(token), retry=retry
        )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_merchant_acquiring_response(response)

    def list_terminals(self, *, page: int = 0, size: int = 50) -> TerminalsPage:
        """Список терминалов торгового эквайринга (постранично)."""
        return self._get(
            _endpoints.TERMINALS, TerminalsPage, params={"page": page, "size": size}
        )

    def list_operations(
        self, terminal_key: str, from_date: str, till: str, *, limit: int
    ) -> OperationList:
        """Операции по терминалу за период (даты — `YYYY-MM-DD`)."""
        return self._get(
            _endpoints.operations_path(terminal_key),
            OperationList,
            params={"from": from_date, "till": till, "limit": limit},
        )
