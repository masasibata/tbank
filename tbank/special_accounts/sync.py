from __future__ import annotations

from typing import Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.core.urls import PROD_URL, SANDBOX_URL
from tbank.special_accounts import _endpoints
from tbank.special_accounts.errors import error_from_special_accounts_response
from tbank.special_accounts.models import OperationsResponse


class SpecialAccountsClient(BaseSyncClient):
    """Синхронный клиент специальных счетов: операции ареста и картотеки ЭТП.

    Работает на обычном хосте по **Bearer**-токену. Суммы — `Decimal` в рублях.
    """

    decimal_body = True

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
        return error_from_special_accounts_response(response)

    def get_arrest_etp_operations(
        self, account_number: str, from_date: str, till: str
    ) -> OperationsResponse:
        """Аресты и картотеки ЭТП по спецсчёту за период (даты — `YYYY-MM-DD`)."""
        return self._get(
            _endpoints.ARREST_ETP,
            OperationsResponse,
            params={"accountNumber": account_number, "from": from_date, "till": till},
        )
