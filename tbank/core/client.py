from __future__ import annotations

import json as _json
import uuid
from decimal import Decimal
from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import httpx
from pydantic import BaseModel, TypeAdapter

from tbank.core.endpoint import Endpoint
from tbank.core.errors import (
    MutualTLSRequiredError,
    TBankAPIError,
    build_api_error,
)
from tbank.core.transport import AsyncTransport, SyncTransport

TResp = TypeVar("TResp", bound=BaseModel)
T = TypeVar("T")

# Парсер ответа: pydantic-модель либо TypeAdapter (списки, полиморфы oneOf).
Parser = Union[Type[T], TypeAdapter[T]]

RequestData = Union[BaseModel, Dict[str, Any], None]


def dump_model(request: Optional[BaseModel]) -> Optional[Dict[str, Any]]:
    """Модель → тело для провода: алиасы, без None, JSON-типы.

    Всегда mode="json": даты → ISO, Decimal → число (через сериализаторы моделей),
    enum → значение. Иначе httpx не сериализует Decimal/datetime в теле POST.
    """
    if request is None:
        return None
    result: Dict[str, Any] = request.model_dump(
        by_alias=True, exclude_none=True, mode="json"
    )
    return result


def parse_as(parser: Parser[T], data: Any) -> T:
    """Валидация данных моделью или TypeAdapter'ом."""
    if isinstance(parser, TypeAdapter):
        return parser.validate_python(data)
    model = cast("Type[BaseModel]", parser)
    return cast(T, model.model_validate(data))


def _idempotency_headers(key: Optional[str]) -> Optional[Dict[str, str]]:
    return {"Idempotency-Key": key} if key is not None else None


def page_params(
    offset: Optional[int] = None, limit: Optional[int] = None, **extra: Any
) -> Dict[str, Any]:
    """Query-параметры пагинации и фильтров без None-значений."""
    params: Dict[str, Any] = {"offset": offset, "limit": limit, **extra}
    return {k: v for k, v in params.items() if v is not None}


def ensure_idempotency_key(key: Optional[str]) -> str:
    """Переданный ключ идемпотентности либо новый uuid4."""
    return key or str(uuid.uuid4())


class _CallMixin:
    #: True → тело парсится с parse_float=Decimal (точные денежные суммы).
    decimal_body: ClassVar[bool] = False

    def _check_error(self, data: Any) -> None:
        """Ошибки уровня тела 200-ответа (переопределяется доменом)."""

    def _parse_body(self, response: httpx.Response) -> Any:
        """Разбор тела ответа (управляется `decimal_body`, можно переопределить)."""
        if self.decimal_body:
            return _json.loads(response.text or "null", parse_float=Decimal)
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

    def _handle(self, response: httpx.Response) -> Any:
        """HTTP-ошибка → исключение, разбор тела, доменная проверка тела."""
        self._raise_for_http(response)
        data = self._parse_body(response)
        self._check_error(data)
        return data

    @staticmethod
    def _coerce_request(
        endpoint: "Endpoint[Any]", request: RequestData
    ) -> Optional[BaseModel]:
        """Приводит запрос к `endpoint.request_model` (принимает и словари)."""
        if request is None:
            return None
        if isinstance(request, BaseModel):
            return request
        if endpoint.request_model is None:
            raise TypeError(
                f"{endpoint.method} {endpoint.path}: эндпоинт не объявил request_model, "
                "передайте pydantic-модель вместо словаря."
            )
        return endpoint.request_model.model_validate(request)

    @staticmethod
    def _prepare_payload(
        endpoint: "Endpoint[Any]", request: Optional[BaseModel]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Возвращает (json_body, query_params): GET → query, иначе → тело."""
        dumped = dump_model(request)
        if dumped is None:
            return None, None
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
        endpoint: "Endpoint[TResp]",
        request: RequestData = None,
    ) -> TResp:
        model = self._coerce_request(endpoint, request)
        transport = self._pick_transport(endpoint.secured)
        json_body, params = self._prepare_payload(endpoint, model)
        response = await transport.request(
            endpoint.method, endpoint.path, json=json_body, params=params
        )
        return endpoint.response_model.model_validate(self._handle(response))

    async def _request(
        self,
        method: str,
        path: str,
        response_model: Type[TResp],
        request: Optional[BaseModel] = None,
        *,
        params: Optional[Dict[str, Any]] = None,
        secured: bool = False,
    ) -> TResp:
        """Прямой вызов с явным путём (для эндпоинтов с path-параметрами)."""
        response = await self._pick_transport(secured).request(
            method, path, json=dump_model(request), params=params
        )
        return response_model.model_validate(self._handle(response))

    async def _get(
        self,
        path: str,
        parser: Parser[T],
        *,
        params: Optional[Dict[str, Any]] = None,
        secured: bool = False,
    ) -> T:
        response = await self._pick_transport(secured).request(
            "GET", path, params=params
        )
        return parse_as(parser, self._handle(response))

    @overload
    async def _send(
        self,
        method: str,
        path: str,
        parser: Parser[T],
        *,
        body: Optional[BaseModel] = ...,
        idempotency_key: Optional[str] = ...,
        params: Optional[Dict[str, Any]] = ...,
        secured: bool = ...,
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
        params: Optional[Dict[str, Any]] = ...,
        secured: bool = ...,
    ) -> None: ...

    async def _send(
        self,
        method: str,
        path: str,
        parser: Optional[Parser[Any]] = None,
        *,
        body: Optional[BaseModel] = None,
        idempotency_key: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        secured: bool = False,
    ) -> Any:
        response = await self._pick_transport(secured).request(
            method,
            path,
            json=dump_model(body),
            params=params,
            headers=_idempotency_headers(idempotency_key),
        )
        if parser is None:
            self._raise_for_http(response)
            return None
        return parse_as(parser, self._handle(response))

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
        endpoint: "Endpoint[TResp]",
        request: RequestData = None,
    ) -> TResp:
        model = self._coerce_request(endpoint, request)
        transport = self._pick_transport(endpoint.secured)
        json_body, params = self._prepare_payload(endpoint, model)
        response = transport.request(
            endpoint.method, endpoint.path, json=json_body, params=params
        )
        return endpoint.response_model.model_validate(self._handle(response))

    def _request(
        self,
        method: str,
        path: str,
        response_model: Type[TResp],
        request: Optional[BaseModel] = None,
        *,
        params: Optional[Dict[str, Any]] = None,
        secured: bool = False,
    ) -> TResp:
        """Прямой вызов с явным путём (для эндпоинтов с path-параметрами)."""
        response = self._pick_transport(secured).request(
            method, path, json=dump_model(request), params=params
        )
        return response_model.model_validate(self._handle(response))

    def _get(
        self,
        path: str,
        parser: Parser[T],
        *,
        params: Optional[Dict[str, Any]] = None,
        secured: bool = False,
    ) -> T:
        response = self._pick_transport(secured).request("GET", path, params=params)
        return parse_as(parser, self._handle(response))

    @overload
    def _send(
        self,
        method: str,
        path: str,
        parser: Parser[T],
        *,
        body: Optional[BaseModel] = ...,
        idempotency_key: Optional[str] = ...,
        params: Optional[Dict[str, Any]] = ...,
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
        params: Optional[Dict[str, Any]] = ...,
        secured: bool = ...,
    ) -> None: ...

    def _send(
        self,
        method: str,
        path: str,
        parser: Optional[Parser[Any]] = None,
        *,
        body: Optional[BaseModel] = None,
        idempotency_key: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        secured: bool = False,
    ) -> Any:
        response = self._pick_transport(secured).request(
            method,
            path,
            json=dump_model(body),
            params=params,
            headers=_idempotency_headers(idempotency_key),
        )
        if parser is None:
            self._raise_for_http(response)
            return None
        return parse_as(parser, self._handle(response))

    def close(self) -> None:
        self._transport.close()
        if self._secured_transport is not None:
            self._secured_transport.close()

    def __enter__(self) -> "BaseSyncClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
