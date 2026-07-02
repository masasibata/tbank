from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, TypeVar

import httpx
from pydantic import BaseModel

from tbank.core.endpoint import Endpoint
from tbank.core.errors import TBankAPIError, build_api_error
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
        """Возвращает (json_body, query_params): GET → query, иначе → тело."""
        if request is None:
            return None, None
        if endpoint.method == "GET":
            return None, request.model_dump(
                by_alias=True, exclude_none=True, mode="json"
            )
        return request.model_dump(by_alias=True, exclude_none=True), None


class BaseAsyncClient(_CallMixin):
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def _call(
        self,
        endpoint: "Endpoint[Any, TResp]",
        request: Optional[BaseModel] = None,
    ) -> TResp:
        json_body, params = self._prepare_payload(endpoint, request)
        response = await self._transport.request(
            endpoint.method, endpoint.path, json=json_body, params=params
        )
        self._raise_for_http(response)
        data = self._parse_body(response)
        self._check_error(data)
        return endpoint.response_model.model_validate(data)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> "BaseAsyncClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


class BaseSyncClient(_CallMixin):
    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def _call(
        self,
        endpoint: "Endpoint[Any, TResp]",
        request: Optional[BaseModel] = None,
    ) -> TResp:
        json_body, params = self._prepare_payload(endpoint, request)
        response = self._transport.request(
            endpoint.method, endpoint.path, json=json_body, params=params
        )
        self._raise_for_http(response)
        data = self._parse_body(response)
        self._check_error(data)
        return endpoint.response_model.model_validate(data)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "BaseSyncClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
