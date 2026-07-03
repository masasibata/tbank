from __future__ import annotations

from typing import Optional

import httpx

from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport, CertTypes, VerifyTypes
from tbank.dolyame import _endpoints
from tbank.dolyame._endpoints import PROD_URL
from tbank.dolyame.auth import DolyameAuth
from tbank.dolyame.errors import error_from_dolyame_response
from tbank.dolyame.models import (
    CommitRequest,
    CompleteDeliveryRequest,
    CorrectionRequest,
    CreateOrderRequest,
    OrderInfo,
    RefundRequest,
    RefundResponse,
)


class DolyameClient(BaseAsyncClient):
    """Асинхронный клиент «Долями» (BNPL Т-Банка).

    Требует mTLS-сертификат (`cert`) + логин/пароль (Basic). Суммы — рубли
    (`Decimal`). Жизненный цикл заказа: create → commit → refund/cancel/delivery.
    """

    decimal_body = True

    def __init__(
        self,
        login: str,
        password: str,
        *,
        cert: Optional[CertTypes] = None,
        base_url: str = PROD_URL,
        verify: VerifyTypes = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[AsyncTransport] = None,
    ) -> None:
        if transport is None:
            if cert is None:
                raise ValueError(
                    "Долями требует mTLS-сертификат: передайте cert=(cert.pem, key.pem)."
                )
            transport = AsyncTransport(
                base_url=base_url,
                auth=DolyameAuth(login, password),
                retry=retry,
                cert=cert,
                verify=verify,
            )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_dolyame_response(response)

    async def create_order(self, request: CreateOrderRequest) -> OrderInfo:
        """Создать заказ (вернёт `link` для клиента и статус)."""
        return await self._request("POST", _endpoints.CREATE_ORDER, OrderInfo, request)

    async def get_order(self, order_id: str) -> OrderInfo:
        """Актуальная информация и статус заказа."""
        return await self._request(
            "GET", _endpoints.order_info_path(order_id), OrderInfo
        )

    async def commit(self, order_id: str, request: CommitRequest) -> OrderInfo:
        """Подтвердить заказ (магазин получает деньги, стартует график)."""
        return await self._request(
            "POST", _endpoints.commit_path(order_id), OrderInfo, request
        )

    async def cancel(self, order_id: str) -> OrderInfo:
        """Отменить заказ."""
        return await self._request("POST", _endpoints.cancel_path(order_id), OrderInfo)

    async def refund(self, order_id: str, request: RefundRequest) -> RefundResponse:
        """Возврат (полный или частичный)."""
        return await self._request(
            "POST", _endpoints.refund_path(order_id), RefundResponse, request
        )

    async def correction(
        self, order_id: str, request: CorrectionRequest
    ) -> RefundResponse:
        """Коррекция корзины заказа."""
        return await self._request(
            "POST", _endpoints.correction_path(order_id), RefundResponse, request
        )

    async def complete_delivery(
        self, order_id: str, request: CompleteDeliveryRequest
    ) -> OrderInfo:
        """Подтвердить успешную доставку."""
        return await self._request(
            "POST", _endpoints.complete_delivery_path(order_id), OrderInfo, request
        )
