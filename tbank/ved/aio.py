from __future__ import annotations

import json
from typing import Any, Dict, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import AsyncTransport
from tbank.ved.errors import CurrencySignatureRequiredError, error_from_ved_response
from tbank.ved.models import (
    AmendContractRequest,
    ApplicationResult,
    ApplicationStatusInfo,
    DeregisterContractRequest,
    RegisterContractRequest,
)
from tbank.ved.signing import CurrencySignature

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"
SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_REGISTRATION = "/api/v1/currency/contracts/openapi/registration"
_AMENDMENT = "/api/v1/currency/contracts/openapi/amendment"
_DEREGISTRATION = "/api/v1/currency/contracts/openapi/deregistration"
_STATUS = "/api/v2/currency/contracts/applications/openapi/status"

T = TypeVar("T", bound=BaseModel)


class VedClient(BaseAsyncClient):
    """Асинхронный клиент ВЭД (валютный контроль): постановка контракта на учёт,
    изменение, снятие с учёта и статус заявления.

    Постановка/изменение/снятие идут на secured-хост (**mTLS**, `cert`) и требуют
    криптоподписи запроса (`signature` — `CurrencySignature(keyId, secret)`);
    статус заявления — на обычном хосте по **Bearer**. Провод — `camelCase`.
    """

    def __init__(
        self,
        token: str,
        *,
        signature: Optional[CurrencySignature] = None,
        base_url: Optional[str] = None,
        secured_base_url: Optional[str] = None,
        sandbox: bool = False,
        cert: Optional[Any] = None,
        verify: Any = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[AsyncTransport] = None,
        secured_transport: Optional[AsyncTransport] = None,
    ) -> None:
        self._signature = signature
        resolved = base_url or (SANDBOX_URL if sandbox else PROD_URL)
        transport = transport or AsyncTransport(
            base_url=resolved, auth=BearerAuth(token), retry=retry
        )
        if secured_transport is None and cert is not None:
            secured_resolved = secured_base_url or (
                SANDBOX_SECURED_URL if sandbox else SECURED_URL
            )
            secured_transport = AsyncTransport(
                base_url=secured_resolved,
                auth=BearerAuth(token),
                retry=retry,
                cert=cert,
                verify=verify,
            )
        super().__init__(transport, secured_transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_ved_response(response)

    async def _signed_post(self, path: str, request: BaseModel, parser: Type[T]) -> T:
        if self._signature is None:
            raise CurrencySignatureRequiredError(
                "Метод требует подпись: передайте signature=CurrencySignature(...)."
            )
        transport = self._pick_transport(secured=True)
        body = _body_bytes(request)
        headers = {
            "Content-Type": "application/json",
            **self._signature.build_headers("POST", path, body),
        }
        response = await transport.request("POST", path, content=body, headers=headers)
        self._raise_for_http(response)
        return parser.model_validate(self._parse_body(response))

    async def register_contract(
        self, request: RegisterContractRequest
    ) -> ApplicationResult:
        """Поставить валютный контракт на учёт (mTLS + подпись)."""
        return await self._signed_post(_REGISTRATION, request, ApplicationResult)

    async def amend_contract(self, request: AmendContractRequest) -> ApplicationResult:
        """Внести изменения в валютный контракт (mTLS + подпись)."""
        return await self._signed_post(_AMENDMENT, request, ApplicationResult)

    async def deregister_contract(
        self, request: DeregisterContractRequest
    ) -> ApplicationResult:
        """Снять валютный контракт с учёта (mTLS + подпись)."""
        return await self._signed_post(_DEREGISTRATION, request, ApplicationResult)

    async def get_application_status(
        self, application_id: str
    ) -> ApplicationStatusInfo:
        """Статус заявления по валютному контракту."""
        response = await self._transport.request(
            "GET", _STATUS, params={"openApiApplicationId": application_id}
        )
        self._raise_for_http(response)
        return ApplicationStatusInfo.model_validate(self._parse_body(response))


def _body_bytes(request: BaseModel) -> bytes:
    payload: Dict[str, Any] = request.model_dump(
        by_alias=True, exclude_none=True, mode="json"
    )
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
