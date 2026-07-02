from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, TypeVar

import httpx
from pydantic import BaseModel

from tbank.core.endpoint import Endpoint
from tbank.core.errors import (
    MutualTLSRequiredError,
    TBankAPIError,
    build_api_error,
)
from tbank.core.transport import AsyncTransport, SyncTransport

TResp = TypeVar("TResp", bound=BaseModel)


class _CallMixin:
    def _check_error(self, data: Any) -> None:
        """Ошибки уровня тела 200-ответа (переопределяется доменом)."""

    def _parse_body(self, response: httpx.Response) -> Any:
        """Разбор тела ответа (переопределяется, напр. для Decimal-парсинга)."""
        return response.json()

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        """Строит исключение из non-2xx ответа (переопределяется под формат домена)."""
        return build_api_error(
            code=str(response.status_code),
            message=response.text,
            http_status=response.status_code,
        )

    def _raise_for_http(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise self._error_from_response(response)

    @staticmethod
    def _prepare_payload(
        endpoint: "Endpoint[Any, Any]", request: Optional[BaseModel]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Возвращает (json_body, query_params): GET → query, иначе → тело.

        Всегда mode="json": даты → ISO, Decimal → число (через сериализаторы моделей),
        enum → значение. Иначе httpx не сериализует Decimal/datetime в теле POST.
        """
        if request is None:
            return None, None
        dumped = request.model_dump(by_alias=True, exclude_none=True, mode="json")
        if endpoint.method == "GET":
            return None, dumped
        return dumped, None


class BaseAsyncClient(_CallMixin):
    def __init__(
        self,
        transport: AsyncTransport,
        secured_transport: Optional[AsyncTransport] = None,
    ) -> None:
        self._transport = transport
        self._secured_transport = secured_transport

    def _pick_transport(self, secured: bool) -> AsyncTransport:
        if not secured:
            return self._transport
        if self._secured_transport is None:
            raise MutualTLSRequiredError(
                "Метод требует mTLS-сертификата: передайте cert=(cert, key) в клиент."
            )
        return self._secured_transport

    async def _call(
        self,
        endpoint: "Endpoint[Any, TResp]",
        request: Optional[BaseModel] = None,
    ) -> TResp:
        transport = self._pick_transport(endpoint.secured)
        json_body, params = self._prepare_payload(endpoint, request)
        response = await transport.request(
            endpoint.method, endpoint.path, json=json_body, params=params
        )
        self._raise_for_http(response)
        data = self._parse_body(response)
        self._check_error(data)
        return endpoint.response_model.model_validate(data)

    async def aclose(self) -> None:
        await self._transport.aclose()
        if self._secured_transport is not None:
            await self._secured_transport.aclose()

    async def __aenter__(self) -> "BaseAsyncClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


class BaseSyncClient(_CallMixin):
    def __init__(
        self,
        transport: SyncTransport,
        secured_transport: Optional[SyncTransport] = None,
    ) -> None:
        self._transport = transport
        self._secured_transport = secured_transport

    def _pick_transport(self, secured: bool) -> SyncTransport:
        if not secured:
            return self._transport
        if self._secured_transport is None:
            raise MutualTLSRequiredError(
                "Метод требует mTLS-сертификата: передайте cert=(cert, key) в клиент."
            )
        return self._secured_transport

    def _call(
        self,
        endpoint: "Endpoint[Any, TResp]",
        request: Optional[BaseModel] = None,
    ) -> TResp:
        transport = self._pick_transport(endpoint.secured)
        json_body, params = self._prepare_payload(endpoint, request)
        response = transport.request(
            endpoint.method, endpoint.path, json=json_body, params=params
        )
        self._raise_for_http(response)
        data = self._parse_body(response)
        self._check_error(data)
        return endpoint.response_model.model_validate(data)

    def close(self) -> None:
        self._transport.close()
        if self._secured_transport is not None:
            self._secured_transport.close()

    def __enter__(self) -> "BaseSyncClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
