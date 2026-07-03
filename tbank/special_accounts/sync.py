from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.special_accounts.errors import error_from_special_accounts_response
from tbank.special_accounts.models import OperationsResponse

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"

_ARREST_ETP = "/api/v1/special-accounts/arrest-etp"


class SpecialAccountsClient(BaseSyncClient):
    """Синхронный клиент специальных счетов: операции ареста и картотеки ЭТП.

    Работает на обычном хосте по **Bearer**-токену. Суммы — `Decimal` в рублях.
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

    def _parse_body(self, response: httpx.Response) -> Any:
        # parse_float=Decimal — точные денежные суммы без float-погрешности.
        return json.loads(response.text or "null", parse_float=Decimal)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_special_accounts_response(response)

    def get_arrest_etp_operations(
        self, account_number: str, from_date: str, till: str
    ) -> OperationsResponse:
        """Аресты и картотеки ЭТП по спецсчёту за период (даты — `YYYY-MM-DD`)."""
        response = self._transport.request(
            "GET",
            _ARREST_ETP,
            params={"accountNumber": account_number, "from": from_date, "till": till},
        )
        self._raise_for_http(response)
        return OperationsResponse.model_validate(self._parse_body(response))
