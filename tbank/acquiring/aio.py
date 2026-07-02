from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter

from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.enums import CheckType, QrDataType
from tbank.acquiring.errors import raise_for_acquiring_result
from tbank.acquiring.models import (
    AddAccountQrRequest,
    AddAccountQrResponse,
    AddAccountQrState,
    AddCardRequest,
    AddCardResponse,
    AddCardState,
    AddCustomerRequest,
    AltPayResponse,
    CancelRequest,
    CancelResponse,
    Card,
    ChargeQrRequest,
    ChargeQrResponse,
    ChargeRequest,
    ChargeResponse,
    CheckOrderRequest,
    CheckOrderResponse,
    ConfirmRequest,
    ConfirmResponse,
    Customer,
    CustomerRequest,
    GetAddAccountQrStateRequest,
    GetAddCardStateRequest,
    GetCardListRequest,
    GetQrRequest,
    GetQrResponse,
    GetQrStateRequest,
    GetStateRequest,
    GetStateResponse,
    InitRequest,
    InitResponse,
    MirPayRequest,
    QrMembersListRequest,
    QrMembersListResponse,
    QrState,
    Receipt,
    RemoveCardRequest,
    RemoveCardResponse,
    ResendRequest,
    ResendResponse,
    SendClosingReceiptRequest,
    SendClosingReceiptResponse,
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
_GET_QR = Endpoint("POST", "/GetQr", GetQrResponse, GetQrRequest)
_QR_MEMBERS = Endpoint(
    "POST", "/QrMembersList", QrMembersListResponse, QrMembersListRequest
)
_ADD_ACCOUNT_QR = Endpoint(
    "POST", "/AddAccountQr", AddAccountQrResponse, AddAccountQrRequest
)
_ADD_ACCOUNT_QR_STATE = Endpoint(
    "POST", "/GetAddAccountQrState", AddAccountQrState, GetAddAccountQrStateRequest
)
_CHARGE_QR = Endpoint("POST", "/ChargeQr", ChargeQrResponse, ChargeQrRequest)
_SEND_CLOSING_RECEIPT = Endpoint(
    "POST", "/SendClosingReceipt", SendClosingReceiptResponse, SendClosingReceiptRequest
)
_ADD_CARD = Endpoint("POST", "/AddCard", AddCardResponse, AddCardRequest)
_ADD_CARD_STATE = Endpoint(
    "POST", "/GetAddCardState", AddCardState, GetAddCardStateRequest
)
_GET_QR_STATE = Endpoint("POST", "/GetQrState", QrState, GetQrStateRequest)
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
        self._terminal_key = terminal_key

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
        receipt: Optional[Receipt] = None,
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
                receipt=receipt,
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

    async def get_qr(
        self,
        payment_id: str,
        *,
        data_type: Optional[QrDataType] = None,
        bank_id: Optional[str] = None,
    ) -> GetQrResponse:
        """Сгенерировать СБП QR/ссылку по платежу (после init)."""
        return await self._call(
            _GET_QR,
            GetQrRequest(payment_id=payment_id, data_type=data_type, bank_id=bank_id),
        )

    async def get_qr_members(self, payment_id: str) -> QrMembersListResponse:
        """Список банков-участников СБП для платежа."""
        return await self._call(
            _QR_MEMBERS, QrMembersListRequest(payment_id=payment_id)
        )

    async def add_account_qr(
        self,
        description: str,
        *,
        data_type: Optional[QrDataType] = None,
        bank_id: Optional[str] = None,
        redirect_due_date: Optional[str] = None,
    ) -> AddAccountQrResponse:
        """Привязать счёт покупателя для СБП-автоплатежей (вернёт QR + RequestKey)."""
        return await self._call(
            _ADD_ACCOUNT_QR,
            AddAccountQrRequest(
                description=description,
                data_type=data_type,
                bank_id=bank_id,
                redirect_due_date=redirect_due_date,
            ),
        )

    async def get_add_account_qr_state(self, request_key: str) -> AddAccountQrState:
        """Статус привязки счёта (AccountToken появляется при ACTIVE)."""
        return await self._call(
            _ADD_ACCOUNT_QR_STATE, GetAddAccountQrStateRequest(request_key=request_key)
        )

    async def charge_qr(
        self,
        payment_id: str,
        account_token: str,
        *,
        ip: Optional[str] = None,
        send_email: Optional[bool] = None,
        info_email: Optional[str] = None,
        bank_member_id: Optional[str] = None,
        receipt: Optional[Receipt] = None,
    ) -> ChargeQrResponse:
        """СБП-автоплатёж по привязанному счёту (AccountToken)."""
        return await self._call(
            _CHARGE_QR,
            ChargeQrRequest(
                payment_id=payment_id,
                account_token=account_token,
                ip=ip,
                send_email=send_email,
                info_email=info_email,
                bank_member_id=bank_member_id,
                receipt=receipt,
            ),
        )

    async def send_closing_receipt(
        self, payment_id: str, receipt: Receipt
    ) -> SendClosingReceiptResponse:
        """Отправить чек при подтверждении двухстадийного платежа."""
        return await self._call(
            _SEND_CLOSING_RECEIPT,
            SendClosingReceiptRequest(payment_id=payment_id, receipt=receipt),
        )

    async def add_card(
        self,
        customer_key: str,
        *,
        check_type: Optional[CheckType] = None,
        ip: Optional[str] = None,
        resident_state: Optional[bool] = None,
    ) -> AddCardResponse:
        """Инициировать привязку карты покупателя (redirect на PaymentURL, без оплаты)."""
        return await self._call(
            _ADD_CARD,
            AddCardRequest(
                customer_key=customer_key,
                check_type=check_type,
                ip=ip,
                resident_state=resident_state,
            ),
        )

    async def get_add_card_state(self, request_key: str) -> AddCardState:
        """Статус привязки карты (COMPLETED → card_id/rebill_id)."""
        return await self._call(
            _ADD_CARD_STATE, GetAddCardStateRequest(request_key=request_key)
        )

    async def get_qr_state(self, payment_id: str) -> QrState:
        """Статус возврата платежа по СБП."""
        return await self._call(_GET_QR_STATE, GetQrStateRequest(payment_id=payment_id))

    # --- Альтернативные способы оплаты (T-Pay / SberPay / MirPay) ---

    async def get_tinkoff_pay_status(self) -> AltPayResponse:
        """Доступность T-Pay и версия терминала (для выбора link/QR)."""
        return await self._request(
            "GET", f"/TinkoffPay/terminals/{self._terminal_key}/status", AltPayResponse
        )

    async def get_tinkoff_pay_link(
        self, payment_id: str, version: str
    ) -> AltPayResponse:
        """Ссылка T-Pay для редиректа в приложение банка (мобильный)."""
        return await self._request(
            "GET",
            f"/TinkoffPay/transactions/{payment_id}/versions/{version}/link",
            AltPayResponse,
        )

    async def get_tinkoff_pay_qr(self, payment_id: str) -> str:
        """T-Pay QR (SVG-изображение) для десктопа."""
        response = await self._transport.request("GET", f"/TinkoffPay/{payment_id}/QR")
        self._raise_for_http(response)
        return response.text

    async def get_sber_pay_link(self, payment_id: str) -> AltPayResponse:
        """Ссылка SberPay для редиректа (мобильный). Путь без версии — досверить."""
        return await self._request(
            "GET", f"/SberPay/transactions/{payment_id}/link", AltPayResponse
        )

    async def get_sber_pay_qr(self, payment_id: str) -> str:
        """SberPay QR (SVG) для десктопа."""
        response = await self._transport.request("GET", f"/SberPay/{payment_id}/QR")
        self._raise_for_http(response)
        return response.text

    async def get_mir_pay_deeplink(self, payment_id: str) -> AltPayResponse:
        """MirPay deeplink в приложение Mir Pay."""
        return await self._request(
            "POST",
            "/MirPay/GetDeepLink",
            AltPayResponse,
            MirPayRequest(payment_id=payment_id),
        )

    # --- Служебные методы ---

    async def check_order(self, order_id: str) -> CheckOrderResponse:
        """Статусы всех платежей по OrderId."""
        return await self._request(
            "POST",
            "/CheckOrder",
            CheckOrderResponse,
            CheckOrderRequest(order_id=order_id),
        )

    async def resend(self) -> ResendResponse:
        """Переотправить недоставленные нотификации."""
        return await self._request("POST", "/Resend", ResendResponse, ResendRequest())
