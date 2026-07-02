from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Iterator, List, Optional

import httpx
from pydantic import TypeAdapter

from tbank.business.errors import error_from_business_response
from tbank.business.models import (
    Account,
    BankStatement,
    BankStatementParams,
    StatementOperation,
    StatementPage,
    StatementParams,
)
from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.endpoint import Endpoint
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"

_ACCOUNTS_PATH = "/api/v2/bank-accounts"
_STATEMENT = Endpoint("GET", "/api/v1/statement", StatementPage, StatementParams)
_BANK_STATEMENT = Endpoint(
    "GET", "/api/v1/bank-statement", BankStatement, BankStatementParams
)
_ACCOUNTS_ADAPTER = TypeAdapter(List[Account])


class BusinessClient(BaseSyncClient):
    """Синхронный клиент T-API (открытый банк Т-Бизнес): счета и выписки."""

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
        return error_from_business_response(response)

    def get_accounts(self) -> List[Account]:
        """Список счетов с балансами."""
        response = self._transport.request("GET", _ACCOUNTS_PATH)
        self._raise_for_http(response)
        return _ACCOUNTS_ADAPTER.validate_python(self._parse_body(response))

    def get_statement(self, params: StatementParams) -> StatementPage:
        """Одна страница выписки операций (курсорная пагинация)."""
        return self._call(_STATEMENT, params)

    def iter_statement(self, params: StatementParams) -> Iterator[StatementOperation]:
        """Все операции выписки: автоматически следует за nextCursor."""
        cursor = params.cursor
        while True:
            page = self.get_statement(params.model_copy(update={"cursor": cursor}))
            for operation in page.operations:
                yield operation
            if not page.next_cursor:
                break
            cursor = page.next_cursor

    def get_bank_statement(self, params: BankStatementParams) -> BankStatement:
        """Выписка за период: сальдо, обороты и операции."""
        return self._call(_BANK_STATEMENT, params)
