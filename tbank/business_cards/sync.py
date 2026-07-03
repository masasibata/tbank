from __future__ import annotations

from typing import List, Optional

import httpx

from tbank.business_cards._endpoints import APPLICATIONS as _APPLICATIONS
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
from tbank.core.client import BaseSyncClient
from tbank.core.client import page_params as _params
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import (
    CertTypes,
    SyncTransport,
    VerifyTypes,
    build_sync_transports,
)
from tbank.core.urls import (
    PROD_URL,
    SANDBOX_SECURED_URL,
    SANDBOX_URL,
    SECURED_URL,
)


class BusinessCardsClient(BaseSyncClient):
    """Синхронный клиент бизнес-карт: выпуск и перевыпуск виртуальных карт,
    реквизиты, блокировка, лимиты (в т.ч. пакетно) и списки карт.

    Перевыпуск, общий расходный лимит, пакетная установка лимитов и методы `v3`
    (список заявок и карт компании) идут на secured-хост и требуют
    **mTLS-сертификата** (`cert`); остальное — на обычном хосте по **Bearer**.
    Суммы — `Decimal` в рублях, провод — `camelCase`.
    """

    decimal_body = True

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        secured_base_url: Optional[str] = None,
        sandbox: bool = False,
        cert: Optional[CertTypes] = None,
        verify: VerifyTypes = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[SyncTransport] = None,
        secured_transport: Optional[SyncTransport] = None,
    ) -> None:
        transport, secured_transport = build_sync_transports(
            token,
            base_url=base_url or (SANDBOX_URL if sandbox else PROD_URL),
            secured_base_url=secured_base_url
            or (SANDBOX_SECURED_URL if sandbox else SECURED_URL),
            cert=cert,
            verify=verify,
            retry=retry,
            transport=transport,
            secured_transport=secured_transport,
        )
        super().__init__(transport, secured_transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_business_cards_response(response)

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
        return self._get(
            "/api/v3/card/virtual/issue/application",
            _APPLICATIONS,
            params={"limit": limit, "offset": offset},
            secured=True,
        )

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
