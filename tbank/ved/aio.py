from __future__ import annotations

from typing import Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from tbank.core.client import BaseAsyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.transport import (
    AsyncTransport,
    CertTypes,
    VerifyTypes,
    build_async_transports,
)
from tbank.core.urls import (
    PROD_URL,
    SANDBOX_SECURED_URL,
    SANDBOX_URL,
    SECURED_URL,
)
from tbank.ved import _endpoints
from tbank.ved.errors import CurrencySignatureRequiredError, error_from_ved_response
from tbank.ved.models import (
    AmendContractRequest,
    ApplicationResult,
    ApplicationStatusInfo,
    DeregisterContractRequest,
    RegisterContractRequest,
)
from tbank.ved.signing import CurrencySignature

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
        cert: Optional[CertTypes] = None,
        verify: VerifyTypes = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[AsyncTransport] = None,
        secured_transport: Optional[AsyncTransport] = None,
    ) -> None:
        self._signature = signature
        transport, secured_transport = build_async_transports(
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
        return error_from_ved_response(response)

    async def _signed_post(self, path: str, request: BaseModel, parser: Type[T]) -> T:
        if self._signature is None:
            raise CurrencySignatureRequiredError(
                "Метод требует подпись: передайте signature=CurrencySignature(...)."
            )
        transport = self._pick_transport(secured=True)
        body = _endpoints.body_bytes(request)
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
        return await self._signed_post(
            _endpoints.REGISTRATION, request, ApplicationResult
        )

    async def amend_contract(self, request: AmendContractRequest) -> ApplicationResult:
        """Внести изменения в валютный контракт (mTLS + подпись)."""
        return await self._signed_post(_endpoints.AMENDMENT, request, ApplicationResult)

    async def deregister_contract(
        self, request: DeregisterContractRequest
    ) -> ApplicationResult:
        """Снять валютный контракт с учёта (mTLS + подпись)."""
        return await self._signed_post(
            _endpoints.DEREGISTRATION, request, ApplicationResult
        )

    async def get_application_status(
        self, application_id: str
    ) -> ApplicationStatusInfo:
        """Статус заявления по валютному контракту."""
        return await self._get(
            _endpoints.STATUS,
            ApplicationStatusInfo,
            params={"openApiApplicationId": application_id},
        )
