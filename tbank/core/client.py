from __future__ import annotations

from typing import Optional, TypeVar

from tbank.core.endpoint import Endpoint
from tbank.core.errors import build_api_error
from tbank.core.models import TBankModel
from tbank.core.transport import AsyncTransport, SyncTransport

TResp = TypeVar("TResp", bound=TBankModel)


class _CallMixin:
    def _check_error(self, data: dict) -> None:
        """Переопределяется в доменных клиентах для ошибок уровня тела ответа."""

    @staticmethod
    def _body(request: Optional[TBankModel]) -> Optional[dict]:
        if request is None:
            return None
        return request.model_dump(by_alias=True, exclude_none=True)

    @staticmethod
    def _raise_for_http(response) -> None:
        if response.status_code >= 400:
            raise build_api_error(
                code=str(response.status_code),
                message=response.text,
                http_status=response.status_code,
            )


class BaseAsyncClient(_CallMixin):
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def _call(
        self,
        endpoint: "Endpoint[TBankModel, TResp]",
        request: Optional[TBankModel] = None,
    ) -> TResp:
        response = await self._transport.request(
            endpoint.method, endpoint.path, json=self._body(request)
        )
        self._raise_for_http(response)
        data = response.json()
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
        endpoint: "Endpoint[TBankModel, TResp]",
        request: Optional[TBankModel] = None,
    ) -> TResp:
        response = self._transport.request(
            endpoint.method, endpoint.path, json=self._body(request)
        )
        self._raise_for_http(response)
        data = response.json()
        self._check_error(data)
        return endpoint.response_model.model_validate(data)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "BaseSyncClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
