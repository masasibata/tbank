from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.deposit.errors import error_from_deposit_response
from tbank.deposit.models import (
    DepositAccountDetails,
    OpenDepositRequest,
    OpenDepositResult,
    ReplenishDepositRequest,
)

SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_DETAILS = "/api/v1/deposit/account/details"
_OPEN = "/api/v1/deposit/account/open"
_REPLENISH = "/api/v1/deposit/account/replenish"


class DepositClient(BaseSyncClient):
    """Синхронный клиент депозитов: карточка счёта, открытие и пополнение.

    Домен работает на secured-хосте и требует **mTLS-сертификата** (`cert`).
    Суммы — `Decimal` в валюте депозита. Провод — `camelCase`.
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
        transport: Optional[SyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_SECURED_URL if sandbox else SECURED_URL)
        transport = transport or SyncTransport(
            base_url=resolved,
            auth=BearerAuth(token),
            cert=cert,
            verify=verify,
            retry=retry,
        )
        super().__init__(transport)

    def _parse_body(self, response: httpx.Response) -> Any:
        # parse_float=Decimal — точные суммы без float-погрешности.
        return json.loads(response.text or "null", parse_float=Decimal)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_deposit_response(response)

    def get_deposit_details(self, agreement_number: str) -> DepositAccountDetails:
        """Карточка депозита: баланс, договор, ставка, условия."""
        response = self._transport.request(
            "GET", _DETAILS, params={"agreementNumber": agreement_number}
        )
        self._raise_for_http(response)
        return DepositAccountDetails.model_validate(self._parse_body(response))

    def open_deposit(self, request: OpenDepositRequest) -> OpenDepositResult:
        """Открыть депозит. Возвращает идентификаторы процесса и заявки."""
        response = self._transport.request("POST", _OPEN, json=_dump(request))
        self._raise_for_http(response)
        return OpenDepositResult.model_validate(self._parse_body(response))

    def replenish_deposit(self, request: ReplenishDepositRequest) -> None:
        """Пополнить депозит с указанного счёта-источника."""
        response = self._transport.request("POST", _REPLENISH, json=_dump(request))
        self._raise_for_http(response)


def _dump(request: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = request.model_dump(
        by_alias=True, exclude_none=True, mode="json"
    )
    return result
