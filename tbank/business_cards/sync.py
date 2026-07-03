from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type, TypeVar, overload

import httpx
from pydantic import BaseModel, TypeAdapter

from tbank.business_cards.errors import error_from_business_cards_response
from tbank.business_cards.models import (
    BlockCardRequest,
    CardInfo,
    CardInfoSeq,
    CardIssueApplicationStatusResult,
    CardLimits,
    CompanyCardsResponse,
    CreateApplicationRequest,
    CreateApplicationResult,
    ReissueApplication,
    ReissueRequest,
    ReissueVirtualCardResult,
    SetBatchLimitsRequest,
    SetBatchLimitsResult,
    SetLimitRequest,
    VirtualCardApplication,
    VirtualCardRequisites,
)
from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"
SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

T = TypeVar("T", bound=BaseModel)

_APPLICATIONS: TypeAdapter[List[VirtualCardApplication]] = TypeAdapter(
    List[VirtualCardApplication]
)


class BusinessCardsClient(BaseSyncClient):
    """Синхронный клиент бизнес-карт: выпуск и перевыпуск виртуальных карт,
    реквизиты, блокировка, лимиты (в т.ч. пакетно) и списки карт.

    Перевыпуск, общий расходный лимит, пакетная установка лимитов и методы `v3`
    (список заявок и карт компании) идут на secured-хост и требуют
    **mTLS-сертификата** (`cert`); остальное — на обычном хосте по **Bearer**.
    Суммы — `Decimal` в рублях, провод — `camelCase`.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        secured_base_url: Optional[str] = None,
        sandbox: bool = False,
        cert: Optional[Any] = None,
        verify: Any = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[SyncTransport] = None,
        secured_transport: Optional[SyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_URL if sandbox else PROD_URL)
        transport = transport or SyncTransport(
            base_url=resolved, auth=BearerAuth(token), retry=retry
        )
        if secured_transport is None and cert is not None:
            secured_resolved = secured_base_url or (
                SANDBOX_SECURED_URL if sandbox else SECURED_URL
            )
            secured_transport = SyncTransport(
                base_url=secured_resolved,
                auth=BearerAuth(token),
                retry=retry,
                cert=cert,
                verify=verify,
            )
        super().__init__(transport, secured_transport)

    def _parse_body(self, response: httpx.Response) -> Any:
        # parse_float=Decimal — точные лимиты без float-погрешности.
        return json.loads(response.text or "null", parse_float=Decimal)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_business_cards_response(response)

    # --- Низкоуровневые помощники ---

    def _get(
        self,
        path: str,
        parser: Type[T],
        *,
        params: Optional[Dict[str, Any]] = None,
        secured: bool = False,
    ) -> T:
        response = self._pick_transport(secured).request("GET", path, params=params)
        self._raise_for_http(response)
        return parser.model_validate(self._parse_body(response))

    @overload
    def _send(
        self,
        method: str,
        path: str,
        parser: Type[T],
        *,
        body: Optional[BaseModel] = ...,
        secured: bool = ...,
    ) -> T: ...

    @overload
    def _send(
        self,
        method: str,
        path: str,
        parser: None = ...,
        *,
        body: Optional[BaseModel] = ...,
        secured: bool = ...,
    ) -> None: ...

    def _send(
        self,
        method: str,
        path: str,
        parser: Any = None,
        *,
        body: Optional[BaseModel] = None,
        secured: bool = False,
    ) -> Any:
        response = self._pick_transport(secured).request(method, path, json=_dump(body))
        self._raise_for_http(response)
        if parser is None:
            return None
        return parser.model_validate(self._parse_body(response))

    # --- Карты ---

    def list_cards(
        self,
        *,
        account_number: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> CardInfoSeq:
        """Список бизнес-карт компании."""
        return self._get(
            "/api/v1/card",
            CardInfoSeq,
            params=_params(accountNumber=account_number, offset=offset, limit=limit),
        )

    def get_card(self, ucid: int) -> CardInfo:
        """Карточка бизнес-карты по её UCID."""
        return self._get(f"/api/v1/card/{ucid}", CardInfo)

    def get_virtual_card_requisites(self, ucid: int) -> VirtualCardRequisites:
        """Реквизиты виртуальной карты (номер, CVC, срок действия)."""
        return self._get(
            f"/api/v1/card/virtual/{ucid}/requisites", VirtualCardRequisites
        )

    def block_card(self, ucid: int, request: BlockCardRequest) -> None:
        """Заблокировать карту."""
        self._send("POST", f"/api/v1/card/{ucid}/block", body=request)

    def list_company_cards(
        self,
        *,
        account_number: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> CompanyCardsResponse:
        """Список карт компании (v3, mTLS)."""
        return self._get(
            "/api/v3/company/card",
            CompanyCardsResponse,
            params=_params(accountNumber=account_number, offset=offset, limit=limit),
            secured=True,
        )

    # --- Выпуск виртуальной карты ---

    def create_virtual_card_application(
        self, request: CreateApplicationRequest
    ) -> CreateApplicationResult:
        """Создать заявку на выпуск виртуальной карты."""
        return self._send(
            "POST",
            "/api/v1/card/virtual/issue/application",
            CreateApplicationResult,
            body=request,
        )

    def get_virtual_card_application(
        self, application_id: str
    ) -> CardIssueApplicationStatusResult:
        """Статус заявки на выпуск виртуальной карты."""
        return self._get(
            f"/api/v1/card/virtual/issue/application/{application_id}",
            CardIssueApplicationStatusResult,
        )

    def list_virtual_card_applications(
        self, *, limit: int, offset: int
    ) -> List[VirtualCardApplication]:
        """Список заявок на выпуск виртуальных карт (v3, mTLS)."""
        response = self._pick_transport(True).request(
            "GET",
            "/api/v3/card/virtual/issue/application",
            params={"limit": limit, "offset": offset},
        )
        self._raise_for_http(response)
        return _APPLICATIONS.validate_python(self._parse_body(response))

    # --- Перевыпуск виртуальной карты ---

    def reissue_virtual_card(self, ucid: int) -> ReissueApplication:
        """Перевыпустить виртуальную карту (mTLS). Возвращает correlationId."""
        return self._send(
            "POST",
            "/api/v1/card/virtual/reissue",
            ReissueApplication,
            body=ReissueRequest(ucid=ucid),
            secured=True,
        )

    def get_reissue_result(self, correlation_id: str) -> ReissueVirtualCardResult:
        """Результат перевыпуска виртуальной карты."""
        return self._get(
            "/api/v1/card/virtual/reissue/result",
            ReissueVirtualCardResult,
            params={"correlationId": correlation_id},
        )

    # --- Лимиты ---

    def get_card_limits(self, ucid: int) -> CardLimits:
        """Текущие лимиты карты (расходный и на снятие наличных)."""
        return self._get(f"/api/v1/card/{ucid}/limits", CardLimits)

    def set_cash_limit(self, ucid: int, request: SetLimitRequest) -> None:
        """Установить лимит на снятие наличных."""
        self._send("POST", f"/api/v1/card/{ucid}/cash-limit", body=request)

    def set_spend_limit(self, ucid: int, request: SetLimitRequest) -> None:
        """Установить общий расходный лимит (mTLS)."""
        self._send(
            "POST", f"/api/v1/card/{ucid}/spend-limit", body=request, secured=True
        )

    def set_batch_limits(self, request: SetBatchLimitsRequest) -> SetBatchLimitsResult:
        """Пакетно установить лимиты для списка карт (v3, mTLS)."""
        return self._send(
            "PUT",
            "/api/v3/card/limits/set_batch",
            SetBatchLimitsResult,
            body=request,
            secured=True,
        )


def _dump(body: Optional[BaseModel]) -> Optional[Dict[str, Any]]:
    if body is None:
        return None
    return body.model_dump(by_alias=True, exclude_none=True, mode="json")


def _params(**kwargs: Any) -> Dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}
