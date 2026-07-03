from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Type, TypeVar, Union, overload

import httpx
from pydantic import BaseModel, TypeAdapter

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport
from tbank.direct_debit.enums import RuleType
from tbank.direct_debit.errors import error_from_direct_debit_response
from tbank.direct_debit.models import (
    AgreementDetails,
    AgreementFile,
    AgreementListResponse,
    AgreementUrl,
    CreatePaymentRequest,
    CreatePaymentRequestResult,
    CreateRuleResult,
    PaymentRequestDetails,
    PaymentRequestFile,
    PaymentRequestListResponse,
    RuleCreate,
    RuleDetails,
    RuleDetailsListResponse,
    RuleListResponse,
    RuleUpdate,
)

SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_V1 = "/api/v1"
_V2 = "/api/v2"

T = TypeVar("T", bound=BaseModel)

# Карточка правила — полиморф (oneOf Recurrent/Trigger) по дискриминатору `type`.
_RULE_DETAILS: TypeAdapter[RuleDetails] = TypeAdapter(RuleDetails)


class DirectDebitClient(BaseAsyncClient):
    """Асинхронный клиент безакцептных списаний: соглашения, правила (рекуррентные
    и триггерные) и платёжные требования.

    Весь домен работает на secured-хосте и требует **mTLS-сертификата** (`cert`).
    Методы создания принимают ключ идемпотентности `idempotency_key` (по умолчанию
    генерируется автоматически). Суммы — `Decimal` в рублях, провод — `camelCase`.
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
        transport: Optional[AsyncTransport] = None,
    ) -> None:
        resolved = base_url or (SANDBOX_SECURED_URL if sandbox else SECURED_URL)
        transport = transport or AsyncTransport(
            base_url=resolved,
            auth=BearerAuth(token),
            cert=cert,
            verify=verify,
            retry=retry,
        )
        super().__init__(transport)

    def _parse_body(self, response: httpx.Response) -> Any:
        # parse_float=Decimal — точные денежные суммы без float-погрешности.
        return json.loads(response.text or "null", parse_float=Decimal)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_direct_debit_response(response)

    # --- Низкоуровневые помощники ---

    async def _get(
        self,
        path: str,
        parser: Union[Type[T], TypeAdapter[T]],
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> T:
        response = await self._transport.request("GET", path, params=params)
        self._raise_for_http(response)
        return _parse(parser, self._parse_body(response))

    @overload
    async def _send(
        self,
        method: str,
        path: str,
        parser: Union[Type[T], TypeAdapter[T]],
        *,
        body: Optional[BaseModel] = ...,
        idempotency_key: Optional[str] = ...,
    ) -> T: ...

    @overload
    async def _send(
        self,
        method: str,
        path: str,
        parser: None = ...,
        *,
        body: Optional[BaseModel] = ...,
        idempotency_key: Optional[str] = ...,
    ) -> None: ...

    async def _send(
        self,
        method: str,
        path: str,
        parser: Any = None,
        *,
        body: Optional[BaseModel] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        headers = (
            {"Idempotency-Key": idempotency_key}
            if idempotency_key is not None
            else None
        )
        response = await self._transport.request(
            method, path, json=_dump(body), headers=headers
        )
        self._raise_for_http(response)
        if parser is None:
            return None
        return _parse(parser, self._parse_body(response))

    # --- Правила ---

    async def list_rules(
        self,
        agreement_id: str,
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> RuleListResponse:
        """Список правил соглашения."""
        return await self._get(
            f"{_V1}/rules",
            RuleListResponse,
            params=_page(offset, limit, agreementId=agreement_id),
        )

    async def list_rules_v2(
        self,
        *,
        agreement_id: Optional[str] = None,
        rule_types: Optional[Sequence[RuleType]] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> RuleDetailsListResponse:
        """Список правил с полной карточкой (v2)."""
        return await self._get(
            f"{_V2}/rules",
            RuleDetailsListResponse,
            params=_page(
                offset,
                limit,
                agreementId=agreement_id,
                ruleTypes=_enum_list(rule_types),
            ),
        )

    async def create_rule(
        self, rule: RuleCreate, *, idempotency_key: Optional[str] = None
    ) -> CreateRuleResult:
        """Создать правило (рекуррентное или триггерное)."""
        return await self._send(
            "POST",
            f"{_V1}/rules",
            CreateRuleResult,
            body=rule,
            idempotency_key=_idem(idempotency_key),
        )

    async def get_rule(self, rule_id: str) -> RuleDetails:
        """Карточка правила."""
        return await self._get(f"{_V1}/rules/{rule_id}", _RULE_DETAILS)

    async def update_rule(self, rule_id: str, rule: RuleUpdate) -> RuleDetails:
        """Обновить правило."""
        return await self._send(
            "PUT", f"{_V1}/rules/{rule_id}", _RULE_DETAILS, body=rule
        )

    async def delete_rule(self, rule_id: str) -> None:
        """Удалить правило."""
        await self._send("DELETE", f"{_V1}/rules/{rule_id}")

    # --- Платёжные требования ---

    async def list_payment_requests(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> PaymentRequestListResponse:
        """Список платёжных требований за период (`YYYY-MM-DD`)."""
        return await self._get(
            f"{_V1}/requests",
            PaymentRequestListResponse,
            params=_page(offset, limit, startDate=start_date, endDate=end_date),
        )

    async def create_payment_request(
        self, request: CreatePaymentRequest, *, idempotency_key: Optional[str] = None
    ) -> CreatePaymentRequestResult:
        """Создать платёжное требование."""
        return await self._send(
            "POST",
            f"{_V1}/requests",
            CreatePaymentRequestResult,
            body=request,
            idempotency_key=_idem(idempotency_key),
        )

    async def get_payment_request(self, request_id: str) -> PaymentRequestDetails:
        """Карточка платёжного требования."""
        return await self._get(f"{_V1}/requests/{request_id}", PaymentRequestDetails)

    async def revoke_payment_request(
        self, request_id: str, *, idempotency_key: Optional[str] = None
    ) -> None:
        """Отозвать платёжное требование."""
        await self._send(
            "POST",
            f"{_V1}/requests/{request_id}/revoke",
            idempotency_key=_idem(idempotency_key),
        )

    async def get_payment_request_file(self, request_id: str) -> PaymentRequestFile:
        """PDF платёжного требования (base64)."""
        return await self._get(f"{_V1}/requests/{request_id}/file", PaymentRequestFile)

    # --- Соглашения ---

    async def list_agreements(
        self, *, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> AgreementListResponse:
        """Список соглашений о безакцептном списании."""
        return await self._get(
            f"{_V1}/agreements", AgreementListResponse, params=_page(offset, limit)
        )

    async def get_agreement(self, agreement_id: str) -> AgreementDetails:
        """Карточка соглашения."""
        return await self._get(f"{_V1}/agreements/{agreement_id}", AgreementDetails)

    async def get_agreement_file(self, agreement_id: str) -> AgreementFile:
        """PDF-файл соглашения (base64)."""
        return await self._get(f"{_V1}/agreements/{agreement_id}/file", AgreementFile)

    async def get_agreement_url(self) -> AgreementUrl:
        """Ссылка на форму подписания соглашения для контрагента."""
        return await self._get(f"{_V1}/agreements/url", AgreementUrl)


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


def _enum_list(values: Optional[Sequence[RuleType]]) -> Optional[List[str]]:
    return [v.value for v in values] if values else None


def _idem(idempotency_key: Optional[str]) -> str:
    return idempotency_key or str(uuid.uuid4())
