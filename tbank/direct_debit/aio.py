from __future__ import annotations

from typing import Optional, Sequence

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.client import ensure_idempotency_key as _idem
from tbank.core.client import page_params as _page
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport, CertTypes, VerifyTypes
from tbank.core.urls import SANDBOX_SECURED_URL, SECURED_URL
from tbank.direct_debit._endpoints import RULE_DETAILS as _RULE_DETAILS
from tbank.direct_debit._endpoints import V1 as _V1
from tbank.direct_debit._endpoints import V2 as _V2
from tbank.direct_debit._endpoints import enum_list as _enum_list
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


class DirectDebitClient(BaseAsyncClient):
    """Асинхронный клиент безакцептных списаний: соглашения, правила (рекуррентные
    и триггерные) и платёжные требования.

    Весь домен работает на secured-хосте и требует **mTLS-сертификата** (`cert`).
    Методы создания принимают ключ идемпотентности `idempotency_key` (по умолчанию
    генерируется автоматически). Суммы — `Decimal` в рублях, провод — `camelCase`.
    """

    decimal_body = True

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        sandbox: bool = False,
        cert: Optional[CertTypes] = None,
        verify: VerifyTypes = True,
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

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_direct_debit_response(response)

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
