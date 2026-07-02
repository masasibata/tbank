from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Optional

import httpx

from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
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

PROD_URL = "https://partner.dolyame.ru/v1"


class DolyameClient(BaseSyncClient):
    """Синхронный клиент «Долями» (BNPL Т-Банка). Требует mTLS + Basic."""

    def __init__(
        self,
        login: str,
        password: str,
        *,
        cert: Optional[Any] = None,
        base_url: str = PROD_URL,
        verify: Any = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[SyncTransport] = None,
    ) -> None:
        if transport is None:
            if cert is None:
                raise ValueError(
                    "Долями требует mTLS-сертификат: передайте cert=(cert.pem, key.pem)."
                )
            transport = SyncTransport(
                base_url=base_url,
                auth=DolyameAuth(login, password),
                retry=retry,
                cert=cert,
                verify=verify,
            )
        super().__init__(transport)

    def _parse_body(self, response: httpx.Response) -> Any:
        return json.loads(response.text or "null", parse_float=Decimal)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_dolyame_response(response)

    def create_order(self, request: CreateOrderRequest) -> OrderInfo:
        """Создать заказ (вернёт `link` для клиента и статус)."""
        return self._request("POST", "/orders/create", OrderInfo, request)

    def get_order(self, order_id: str) -> OrderInfo:
        """Актуальная информация и статус заказа."""
        return self._request("GET", f"/orders/{order_id}/info", OrderInfo)

    def commit(self, order_id: str, request: CommitRequest) -> OrderInfo:
        """Подтвердить заказ (магазин получает деньги, стартует график)."""
        return self._request("POST", f"/orders/{order_id}/commit", OrderInfo, request)

    def cancel(self, order_id: str) -> OrderInfo:
        """Отменить заказ."""
        return self._request("POST", f"/orders/{order_id}/cancel", OrderInfo)

    def refund(self, order_id: str, request: RefundRequest) -> RefundResponse:
        """Возврат (полный или частичный)."""
        return self._request(
            "POST", f"/orders/{order_id}/refund", RefundResponse, request
        )

    def correction(self, order_id: str, request: CorrectionRequest) -> RefundResponse:
        """Коррекция корзины заказа."""
        return self._request(
            "POST", f"/orders/{order_id}/correction", RefundResponse, request
        )

    def complete_delivery(
        self, order_id: str, request: CompleteDeliveryRequest
    ) -> OrderInfo:
        """Подтвердить успешную доставку."""
        return self._request(
            "POST", f"/orders/{order_id}/complete_delivery", OrderInfo, request
        )
