from __future__ import annotations

from typing import Any, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.merchant_acquiring.errors import error_from_merchant_acquiring_response
from tbank.merchant_acquiring.models import OperationList, TerminalsPage

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"

_TERMINALS = "/api/v1/tacq/terminals"
_OPERATIONS = "/api/v1/tacq/operations/terminal"


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
        response = self._transport.request(
            "GET", _TERMINALS, params={"page": page, "size": size}
        )
        self._raise_for_http(response)
        return TerminalsPage.model_validate(self._parse_body(response))

    def list_operations(
        self, terminal_key: str, from_date: str, till: str, *, limit: int
    ) -> OperationList:
        """Операции по терминалу за период (даты — `YYYY-MM-DD`)."""
        response = self._transport.request(
            "GET",
            f"{_OPERATIONS}/{terminal_key}",
            params={"from": from_date, "till": till, "limit": limit},
        )
        self._raise_for_http(response)
        return OperationList.model_validate(self._parse_body(response))
