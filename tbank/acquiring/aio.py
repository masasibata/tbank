from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter

from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.errors import raise_for_acquiring_result
from tbank.acquiring.models import (
    AddCustomerRequest,
    CancelRequest,
    CancelResponse,
    Card,
    ChargeRequest,
    ChargeResponse,
    ConfirmRequest,
    ConfirmResponse,
    Customer,
    CustomerRequest,
    GetCardListRequest,
    GetStateRequest,
    GetStateResponse,
    InitRequest,
    InitResponse,
    RemoveCardRequest,
    RemoveCardResponse,
)
from tbank.core.client import BaseAsyncClient
from tbank.core.endpoint import Endpoint
from tbank.core.models import Kopecks
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport

BASE_URL = "https://securepay.tinkoff.ru/v2"

_INIT = Endpoint("POST", "/Init", InitResponse, InitRequest)
_GET_STATE = Endpoint("POST", "/GetState", GetStateResponse, GetStateRequest)
_CONFIRM = Endpoint("POST", "/Confirm", ConfirmResponse, ConfirmRequest)
_CANCEL = Endpoint("POST", "/Cancel", CancelResponse, CancelRequest)
_CHARGE = Endpoint("POST", "/Charge", ChargeResponse, ChargeRequest)
_ADD_CUSTOMER = Endpoint("POST", "/AddCustomer", Customer, AddCustomerRequest)
_GET_CUSTOMER = Endpoint("POST", "/GetCustomer", Customer, CustomerRequest)
_REMOVE_CUSTOMER = Endpoint("POST", "/RemoveCustomer", Customer, CustomerRequest)
_REMOVE_CARD = Endpoint("POST", "/RemoveCard", RemoveCardResponse, RemoveCardRequest)
_CARDS_ADAPTER = TypeAdapter(List[Card])


class AcquiringClient(BaseAsyncClient):
    """Асинхронный клиент интернет-эквайринга Т-Банка (redirect-поток)."""

    def __init__(
        self,
        terminal_key: str,
        password: str,
        *,
        base_url: str = BASE_URL,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[AsyncTransport] = None,
    ) -> None:
        transport = transport or AsyncTransport(
            base_url=base_url,
            auth=TokenSignatureAuth(terminal_key, password),
            retry=retry,
        )
        super().__init__(transport)

    def _check_error(self, data: Dict[str, Any]) -> None:
        raise_for_acquiring_result(data)

    async def init(self, request: InitRequest) -> InitResponse:
        return await self._call(_INIT, request)

    async def get_state(self, payment_id: str) -> GetStateResponse:
        return await self._call(_GET_STATE, GetStateRequest(payment_id=payment_id))

    async def confirm(
        self, payment_id: str, amount: Optional[Kopecks] = None
    ) -> ConfirmResponse:
        return await self._call(
            _CONFIRM, ConfirmRequest(payment_id=payment_id, amount=amount)
        )

    async def cancel(
        self, payment_id: str, amount: Optional[Kopecks] = None
    ) -> CancelResponse:
        return await self._call(
            _CANCEL, CancelRequest(payment_id=payment_id, amount=amount)
        )

    async def charge(
        self,
        payment_id: str,
        rebill_id: str,
        *,
        ip: Optional[str] = None,
        send_email: Optional[bool] = None,
        info_email: Optional[str] = None,
    ) -> ChargeResponse:
        """Рекуррентный платёж по сохранённой карте (RebillId), без участия покупателя."""
        return await self._call(
            _CHARGE,
            ChargeRequest(
                payment_id=payment_id,
                rebill_id=rebill_id,
                ip=ip,
                send_email=send_email,
                info_email=info_email,
            ),
        )

    async def add_customer(
        self,
        customer_key: str,
        *,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> Customer:
        """Зарегистрировать покупателя (для сохранения карт)."""
        return await self._call(
            _ADD_CUSTOMER,
            AddCustomerRequest(
                customer_key=customer_key, email=email, phone=phone, ip=ip
            ),
        )

    async def get_customer(
        self, customer_key: str, *, ip: Optional[str] = None
    ) -> Customer:
        """Данные покупателя."""
        return await self._call(
            _GET_CUSTOMER, CustomerRequest(customer_key=customer_key, ip=ip)
        )

    async def remove_customer(
        self, customer_key: str, *, ip: Optional[str] = None
    ) -> Customer:
        """Удалить покупателя."""
        return await self._call(
            _REMOVE_CUSTOMER, CustomerRequest(customer_key=customer_key, ip=ip)
        )

    async def get_card_list(
        self,
        customer_key: str,
        *,
        saved_card: Optional[bool] = None,
        ip: Optional[str] = None,
    ) -> List[Card]:
        """Список сохранённых карт покупателя (ответ — массив, включая удалённые)."""
        request = GetCardListRequest(
            customer_key=customer_key, saved_card=saved_card, ip=ip
        )
        body = request.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = await self._transport.request("POST", "/GetCardList", json=body)
        self._raise_for_http(response)
        data = self._parse_body(response)
        if isinstance(data, dict):  # при ошибке приходит объект, а не массив
            raise_for_acquiring_result(data)
        return _CARDS_ADAPTER.validate_python(data)

    async def remove_card(
        self, customer_key: str, card_id: str, *, ip: Optional[str] = None
    ) -> RemoveCardResponse:
        """Удалить карту покупателя."""
        return await self._call(
            _REMOVE_CARD,
            RemoveCardRequest(customer_key=customer_key, card_id=card_id, ip=ip),
        )
