from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Type, TypeVar, Union, overload

import httpx
from pydantic import BaseModel, TypeAdapter

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import SyncTransport
from tbank.nominal_accounts.errors import error_from_nominal_response
from tbank.nominal_accounts.models import (
    AddCardRequest,
    AddCardRequestResponse,
    BalanceListResponse,
    BankDetailsListResponse,
    BankDetailsRequest,
    BankDetailsResponse,
    BeneficiaryListResponse,
    BeneficiaryRequest,
    BeneficiaryResponse,
    BeneficiaryScoringListResponse,
    CreatePaymentRequest,
    CreateTransferRequest,
    DealListResponse,
    DealRequest,
    DealResponse,
    DealValidity,
    DeponentListResponse,
    DeponentRequest,
    DeponentResponse,
    HoldListResponse,
    IdentifyIncomingTransactionRequest,
    IncomingTransactionListResponse,
    PaymentListResponse,
    PaymentResponse,
    RecipientListResponse,
    RecipientRequest,
    RecipientResponse,
    RetryPaymentResponse,
    StepListResponse,
    StepRequest,
    StepResponse,
    TransferListResponse,
    TransferResponse,
    UpdateRecipientBankDetailsRequest,
)

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"
SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_NA = "/api/v1/nominal-accounts"
_NA_V2 = "/api/v2/nominal-accounts"

T = TypeVar("T", bound=BaseModel)

# Ответы-полиморфы (oneOf) валидируются через TypeAdapter по дискриминатору.
_BENEFICIARY: TypeAdapter[BeneficiaryResponse] = TypeAdapter(BeneficiaryResponse)
_ADD_CARD: TypeAdapter[AddCardRequestResponse] = TypeAdapter(AddCardRequestResponse)
_BANK_DETAILS: TypeAdapter[BankDetailsResponse] = TypeAdapter(BankDetailsResponse)
_PAYMENT: TypeAdapter[PaymentResponse] = TypeAdapter(PaymentResponse)


class NominalAccountsClient(BaseSyncClient):
    """Синхронный клиент номинальных счетов: бенефициары и их банковские
    реквизиты, скоринг, сделки/этапы/депоненты/реципиенты, платежи, балансы,
    холды и переводы между виртуальными счетами.

    Просмотр карточек сделки, этапа и платежа, проверка сделки и все операции с
    переводами идут на secured-хост и требуют **mTLS-сертификата** (`cert`);
    остальные методы — на обычном хосте по **Bearer**-токену. Методы создания
    ресурсов принимают ключ идемпотентности `idempotency_key` (по умолчанию
    генерируется автоматически).
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
        # parse_float=Decimal — точные денежные суммы без float-погрешности.
        return json.loads(response.text or "null", parse_float=Decimal)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_nominal_response(response)

    # --- Низкоуровневые помощники ---

    def _get(
        self,
        path: str,
        parser: Union[Type[T], TypeAdapter[T]],
        *,
        params: Optional[Dict[str, Any]] = None,
        secured: bool = False,
    ) -> T:
        response = self._pick_transport(secured).request("GET", path, params=params)
        self._raise_for_http(response)
        return _parse(parser, self._parse_body(response))

    @overload
    def _send(
        self,
        method: str,
        path: str,
        parser: Union[Type[T], TypeAdapter[T]],
        *,
        body: Optional[BaseModel] = ...,
        idempotency_key: Optional[str] = ...,
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
        idempotency_key: Optional[str] = ...,
        secured: bool = ...,
    ) -> None: ...

    def _send(
        self,
        method: str,
        path: str,
        parser: Any = None,
        *,
        body: Optional[BaseModel] = None,
        idempotency_key: Optional[str] = None,
        secured: bool = False,
    ) -> Any:
        headers = (
            {"Idempotency-Key": idempotency_key}
            if idempotency_key is not None
            else None
        )
        response = self._pick_transport(secured).request(
            method, path, json=_dump(body), headers=headers
        )
        self._raise_for_http(response)
        if parser is None:
            return None
        return _parse(parser, self._parse_body(response))

    # --- Бенефициары ---

    def list_beneficiaries(
        self, *, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> BeneficiaryListResponse:
        """Список бенефициаров компании."""
        return self._get(
            f"{_NA}/beneficiaries", BeneficiaryListResponse, params=_page(offset, limit)
        )

    def create_beneficiary(
        self, request: BeneficiaryRequest, *, idempotency_key: Optional[str] = None
    ) -> BeneficiaryResponse:
        """Создать бенефициара."""
        return self._send(
            "POST",
            f"{_NA}/beneficiaries",
            _BENEFICIARY,
            body=request,
            idempotency_key=_idem(idempotency_key),
        )

    def get_beneficiary(self, beneficiary_id: str) -> BeneficiaryResponse:
        """Карточка бенефициара."""
        return self._get(f"{_NA}/beneficiaries/{beneficiary_id}", _BENEFICIARY)

    def update_beneficiary(
        self, beneficiary_id: str, request: BeneficiaryRequest
    ) -> BeneficiaryResponse:
        """Обновить бенефициара."""
        return self._send(
            "PUT", f"{_NA}/beneficiaries/{beneficiary_id}", _BENEFICIARY, body=request
        )

    def create_add_card_request(
        self,
        beneficiary_id: str,
        request: AddCardRequest,
        *,
        idempotency_key: Optional[str] = None,
    ) -> AddCardRequestResponse:
        """Создать запрос на добавление карты бенефициару."""
        return self._send(
            "POST",
            f"{_NA}/beneficiaries/{beneficiary_id}/add-card-requests",
            _ADD_CARD,
            body=request,
            idempotency_key=_idem(idempotency_key),
        )

    def get_add_card_request(
        self, beneficiary_id: str, add_card_request_id: str
    ) -> AddCardRequestResponse:
        """Статус запроса на добавление карты."""
        return self._get(
            f"{_NA}/beneficiaries/{beneficiary_id}"
            f"/add-card-requests/{add_card_request_id}",
            _ADD_CARD,
        )

    def list_bank_details(
        self,
        beneficiary_id: str,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> BankDetailsListResponse:
        """Список банковских реквизитов бенефициара."""
        return self._get(
            f"{_NA}/beneficiaries/{beneficiary_id}/bank-details",
            BankDetailsListResponse,
            params=_page(offset, limit),
        )

    def create_bank_details(
        self,
        beneficiary_id: str,
        request: BankDetailsRequest,
        *,
        idempotency_key: Optional[str] = None,
    ) -> BankDetailsResponse:
        """Добавить банковские реквизиты бенефициару."""
        return self._send(
            "POST",
            f"{_NA}/beneficiaries/{beneficiary_id}/bank-details",
            _BANK_DETAILS,
            body=request,
            idempotency_key=_idem(idempotency_key),
        )

    def get_bank_details(
        self, beneficiary_id: str, bank_details_id: str
    ) -> BankDetailsResponse:
        """Карточка банковских реквизитов."""
        return self._get(
            f"{_NA}/beneficiaries/{beneficiary_id}/bank-details/{bank_details_id}",
            _BANK_DETAILS,
        )

    def update_bank_details(
        self, beneficiary_id: str, bank_details_id: str, request: BankDetailsRequest
    ) -> BankDetailsResponse:
        """Обновить банковские реквизиты."""
        return self._send(
            "PUT",
            f"{_NA}/beneficiaries/{beneficiary_id}/bank-details/{bank_details_id}",
            _BANK_DETAILS,
            body=request,
        )

    def delete_bank_details(self, beneficiary_id: str, bank_details_id: str) -> None:
        """Удалить банковские реквизиты."""
        self._send(
            "DELETE",
            f"{_NA}/beneficiaries/{beneficiary_id}/bank-details/{bank_details_id}",
        )

    def set_default_bank_details(
        self, beneficiary_id: str, bank_details_id: str
    ) -> None:
        """Сделать реквизиты основными для бенефициара."""
        self._send(
            "POST",
            f"{_NA}/beneficiaries/{beneficiary_id}"
            f"/bank-details/{bank_details_id}/set-default",
        )

    def get_beneficiaries_scoring(
        self,
        *,
        beneficiary_id: Optional[str] = None,
        passed: Optional[bool] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> BeneficiaryScoringListResponse:
        """Результаты проверки бенефициаров в финансовом мониторинге."""
        return self._get(
            f"{_NA_V2}/beneficiaries/scoring",
            BeneficiaryScoringListResponse,
            params=_page(offset, limit, beneficiaryId=beneficiary_id, passed=passed),
        )

    # --- Сделки ---

    def list_deals(
        self, *, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> DealListResponse:
        """Список сделок."""
        return self._get(f"{_NA}/deals", DealListResponse, params=_page(offset, limit))

    def create_deal(
        self, request: DealRequest, *, idempotency_key: Optional[str] = None
    ) -> DealResponse:
        """Создать сделку (черновик)."""
        return self._send(
            "POST",
            f"{_NA}/deals",
            DealResponse,
            body=request,
            idempotency_key=_idem(idempotency_key),
        )

    def get_deal(self, deal_id: str) -> DealResponse:
        """Карточка сделки (mTLS)."""
        return self._get(f"{_NA}/deals/{deal_id}", DealResponse, secured=True)

    def delete_deal(self, deal_id: str) -> None:
        """Удалить сделку-черновик."""
        self._send("DELETE", f"{_NA}/deals/{deal_id}")

    def accept_deal(self, deal_id: str) -> None:
        """Принять (согласовать) сделку."""
        self._send("POST", f"{_NA}/deals/{deal_id}/accept")

    def cancel_deal(self, deal_id: str) -> None:
        """Отменить сделку."""
        self._send("POST", f"{_NA}/deals/{deal_id}/cancel")

    def draft_deal(self, deal_id: str) -> None:
        """Вернуть сделку в черновик."""
        self._send("POST", f"{_NA}/deals/{deal_id}/draft")

    def get_deal_validity(self, deal_id: str) -> DealValidity:
        """Проверить возможность проведения платежей по сделке (mTLS)."""
        return self._get(f"{_NA}/deals/{deal_id}/is-valid", DealValidity, secured=True)

    # --- Этапы сделки ---

    def list_steps(
        self,
        deal_id: str,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> StepListResponse:
        """Список этапов сделки."""
        return self._get(
            f"{_NA}/deals/{deal_id}/steps",
            StepListResponse,
            params=_page(offset, limit),
        )

    def create_step(
        self,
        deal_id: str,
        request: StepRequest,
        *,
        idempotency_key: Optional[str] = None,
    ) -> StepResponse:
        """Создать этап сделки."""
        return self._send(
            "POST",
            f"{_NA}/deals/{deal_id}/steps",
            StepResponse,
            body=request,
            idempotency_key=_idem(idempotency_key),
        )

    def get_step(self, deal_id: str, step_id: str) -> StepResponse:
        """Карточка этапа сделки (mTLS)."""
        return self._get(
            f"{_NA}/deals/{deal_id}/steps/{step_id}", StepResponse, secured=True
        )

    def update_step(
        self, deal_id: str, step_id: str, request: StepRequest
    ) -> StepResponse:
        """Обновить этап сделки."""
        return self._send(
            "PUT", f"{_NA}/deals/{deal_id}/steps/{step_id}", StepResponse, body=request
        )

    def delete_step(self, deal_id: str, step_id: str) -> None:
        """Удалить этап сделки."""
        self._send("DELETE", f"{_NA}/deals/{deal_id}/steps/{step_id}")

    def complete_step(self, deal_id: str, step_id: str) -> None:
        """Завершить этап сделки (провести выплаты)."""
        self._send("POST", f"{_NA}/deals/{deal_id}/steps/{step_id}/complete")

    # --- Депоненты этапа ---

    def list_deponents(
        self,
        deal_id: str,
        step_id: str,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> DeponentListResponse:
        """Список депонентов этапа сделки."""
        return self._get(
            f"{_NA}/deals/{deal_id}/steps/{step_id}/deponents",
            DeponentListResponse,
            params=_page(offset, limit),
        )

    def get_deponent(
        self, deal_id: str, step_id: str, beneficiary_id: str
    ) -> DeponentResponse:
        """Карточка депонента этапа сделки."""
        return self._get(
            f"{_NA}/deals/{deal_id}/steps/{step_id}/deponents/{beneficiary_id}",
            DeponentResponse,
        )

    def set_deponent(
        self,
        deal_id: str,
        step_id: str,
        beneficiary_id: str,
        request: DeponentRequest,
    ) -> DeponentResponse:
        """Добавить/обновить депонента этапа сделки."""
        return self._send(
            "PUT",
            f"{_NA}/deals/{deal_id}/steps/{step_id}/deponents/{beneficiary_id}",
            DeponentResponse,
            body=request,
        )

    def delete_deponent(self, deal_id: str, step_id: str, beneficiary_id: str) -> None:
        """Удалить депонента этапа сделки."""
        self._send(
            "DELETE",
            f"{_NA}/deals/{deal_id}/steps/{step_id}/deponents/{beneficiary_id}",
        )

    # --- Реципиенты этапа ---

    def list_recipients(
        self,
        deal_id: str,
        step_id: str,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> RecipientListResponse:
        """Список реципиентов этапа сделки."""
        return self._get(
            f"{_NA}/deals/{deal_id}/steps/{step_id}/recipients",
            RecipientListResponse,
            params=_page(offset, limit),
        )

    def create_recipient(
        self,
        deal_id: str,
        step_id: str,
        request: RecipientRequest,
        *,
        idempotency_key: Optional[str] = None,
    ) -> RecipientResponse:
        """Добавить реципиента этапа сделки."""
        return self._send(
            "POST",
            f"{_NA}/deals/{deal_id}/steps/{step_id}/recipients",
            RecipientResponse,
            body=request,
            idempotency_key=_idem(idempotency_key),
        )

    def get_recipient(
        self, deal_id: str, step_id: str, recipient_id: str
    ) -> RecipientResponse:
        """Карточка реципиента этапа сделки."""
        return self._get(
            f"{_NA}/deals/{deal_id}/steps/{step_id}/recipients/{recipient_id}",
            RecipientResponse,
        )

    def update_recipient(
        self,
        deal_id: str,
        step_id: str,
        recipient_id: str,
        request: RecipientRequest,
    ) -> RecipientResponse:
        """Обновить реципиента этапа сделки."""
        return self._send(
            "PUT",
            f"{_NA}/deals/{deal_id}/steps/{step_id}/recipients/{recipient_id}",
            RecipientResponse,
            body=request,
        )

    def delete_recipient(self, deal_id: str, step_id: str, recipient_id: str) -> None:
        """Удалить реципиента этапа сделки."""
        self._send(
            "DELETE",
            f"{_NA}/deals/{deal_id}/steps/{step_id}/recipients/{recipient_id}",
        )

    def update_recipient_bank_details(
        self,
        deal_id: str,
        step_id: str,
        recipient_id: str,
        request: UpdateRecipientBankDetailsRequest,
    ) -> None:
        """Обновить банковские реквизиты реципиента."""
        self._send(
            "POST",
            f"{_NA}/deals/{deal_id}/steps/{step_id}"
            f"/recipients/{recipient_id}/update-bank-details",
            body=request,
        )

    # --- Платежи ---

    def list_payments(
        self,
        *,
        beneficiary_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        account_number: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> PaymentListResponse:
        """Список платежей с номинального счёта."""
        return self._get(
            f"{_NA}/payments",
            PaymentListResponse,
            params=_page(
                offset,
                limit,
                beneficiaryId=beneficiary_id,
                dealId=deal_id,
                accountNumber=account_number,
            ),
        )

    def create_payment(
        self, request: CreatePaymentRequest, *, idempotency_key: Optional[str] = None
    ) -> PaymentResponse:
        """Создать платёж (обычный или налоговый)."""
        return self._send(
            "POST",
            f"{_NA}/payments",
            _PAYMENT,
            body=request,
            idempotency_key=_idem(idempotency_key),
        )

    def get_payment(self, payment_id: str) -> PaymentResponse:
        """Карточка платежа (mTLS)."""
        return self._get(f"{_NA}/payments/{payment_id}", _PAYMENT, secured=True)

    def retry_payment(self, payment_id: str) -> RetryPaymentResponse:
        """Повторить неуспешный платёж."""
        return self._send(
            "POST", f"{_NA}/payments/{payment_id}/retry", RetryPaymentResponse
        )

    # --- Неидентифицированные пополнения ---

    def list_incoming_transactions(
        self,
        *,
        account_number: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> IncomingTransactionListResponse:
        """Список неидентифицированных пополнений."""
        return self._get(
            f"{_NA}/incoming-transactions",
            IncomingTransactionListResponse,
            params=_page(offset, limit, accountNumber=account_number),
        )

    def identify_incoming_transaction(
        self, operation_id: str, request: IdentifyIncomingTransactionRequest
    ) -> None:
        """Идентифицировать пополнение (распределить по бенефициарам)."""
        self._send(
            "POST",
            f"{_NA}/incoming-transactions/{operation_id}/identify",
            body=request,
        )

    # --- Виртуальные счета ---

    def list_balances(
        self,
        *,
        account_number: Optional[str] = None,
        beneficiary_id: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> BalanceListResponse:
        """Балансы бенефициаров на виртуальных счетах."""
        return self._get(
            f"{_NA}/virtual-accounts/balances",
            BalanceListResponse,
            params=_page(
                offset,
                limit,
                accountNumber=account_number,
                beneficiaryId=beneficiary_id,
            ),
        )

    def list_holds(
        self,
        *,
        account_number: Optional[str] = None,
        beneficiary_id: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> HoldListResponse:
        """Заблокированные средства (холды) на виртуальных счетах."""
        return self._get(
            f"{_NA}/virtual-accounts/holds",
            HoldListResponse,
            params=_page(
                offset,
                limit,
                accountNumber=account_number,
                beneficiaryId=beneficiary_id,
            ),
        )

    def list_transfers(
        self,
        account_number: str,
        *,
        deal_id: Optional[str] = None,
        from_beneficiary_id: Optional[str] = None,
        to_beneficiary_id: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> TransferListResponse:
        """Список переводов между виртуальными счетами (mTLS)."""
        return self._get(
            f"{_NA}/virtual-accounts/transfers",
            TransferListResponse,
            params=_page(
                offset,
                limit,
                accountNumber=account_number,
                dealId=deal_id,
                fromBeneficiaryId=from_beneficiary_id,
                toBeneficiaryId=to_beneficiary_id,
            ),
            secured=True,
        )

    def create_transfer(
        self, request: CreateTransferRequest, *, idempotency_key: Optional[str] = None
    ) -> TransferResponse:
        """Создать перевод между виртуальными счетами (mTLS)."""
        return self._send(
            "POST",
            f"{_NA}/virtual-accounts/transfers",
            TransferResponse,
            body=request,
            idempotency_key=_idem(idempotency_key),
            secured=True,
        )

    def get_transfer(self, transfer_id: str) -> TransferResponse:
        """Карточка перевода между виртуальными счетами (mTLS)."""
        return self._get(
            f"{_NA}/virtual-accounts/transfers/{transfer_id}",
            TransferResponse,
            secured=True,
        )


def _dump(body: Optional[BaseModel]) -> Optional[Dict[str, Any]]:
    if body is None:
        return None
    return body.model_dump(by_alias=True, exclude_none=True, mode="json")


def _parse(parser: Union[Type[T], TypeAdapter[T]], data: Any) -> T:
    if isinstance(parser, TypeAdapter):
        return parser.validate_python(data)
    return parser.model_validate(data)


def _page(offset: Optional[int], limit: Optional[int], **extra: Any) -> Dict[str, Any]:
    params: Dict[str, Any] = {"offset": offset, "limit": limit, **extra}
    return {k: v for k, v in params.items() if v is not None}


def _idem(idempotency_key: Optional[str]) -> str:
    return idempotency_key or str(uuid.uuid4())
