from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

import httpx

from tbank.core.auth import AuthStrategy, Body, Headers, NoAuth
from tbank.core.errors import TBankNetworkError, TBankTimeoutError
from tbank.core.retry import RetryPolicy, compute_delay, should_retry

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=5.0)


def _drop_json_content_type(
    headers: "Headers",
    data: Optional[Dict[str, Any]],
    files: Optional[Any],
) -> "Headers":
    """Для multipart/form-запросов убирает дефолтный JSON-Content-Type, чтобы httpx
    выставил свой (с boundary). Для `content` (сырое тело) Content-Type задаёт сам
    вызывающий, поэтому его не трогаем."""
    if data is None and files is None:
        return headers
    return {
        k: v
        for k, v in headers.items()
        if not (
            k.lower() == "content-type" and v.lower().startswith("application/json")
        )
    }


class _TransportBase:
    def __init__(
        self,
        *,
        base_url: str,
        auth: Optional[AuthStrategy] = None,
        retry: Optional[RetryPolicy] = None,
        timeout: Optional[httpx.Timeout] = None,
        user_agent: str = "tbank",
        cert: Optional[Any] = None,
        verify: Any = True,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth: AuthStrategy = auth or NoAuth()
        self._retry = retry or RetryPolicy()
        self._timeout = timeout or DEFAULT_TIMEOUT
        self._cert = cert  # mTLS: (cert.pem, key.pem) или путь
        self._verify = verify  # CA-бандл или True
        self._base_headers: Headers = {
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        }

    def _prepare(
        self, json: Body, headers: Optional[Dict[str, str]]
    ) -> Tuple[Body, Headers]:
        merged: Headers = {**self._base_headers, **(headers or {})}
        return self._auth.apply(json, merged)

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    @staticmethod
    def _retry_after(response: httpx.Response) -> Optional[float]:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None


class AsyncTransport(_TransportBase):
    def __init__(
        self, *, client: Optional[httpx.AsyncClient] = None, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self._client = client or httpx.AsyncClient(
            timeout=self._timeout, cert=self._cert, verify=self._verify
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Body = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Any] = None,
        content: Optional[Any] = None,
    ) -> httpx.Response:
        url = self._url(path)
        body, merged = self._prepare(json, headers)
        merged = _drop_json_content_type(merged, data, files)
        attempt = 0
        while True:
            attempt += 1
            try:
                response = await self._client.request(
                    method,
                    url,
                    json=body,
                    params=params,
                    headers=merged,
                    data=data,
                    files=files,
                    content=content,
                )
            except httpx.TimeoutException as exc:
                if should_retry(self._retry, status=None, attempt=attempt):
                    await asyncio.sleep(compute_delay(self._retry, attempt=attempt))
                    continue
                raise TBankTimeoutError(str(exc)) from exc
            except httpx.HTTPError as exc:
                if should_retry(self._retry, status=None, attempt=attempt):
                    await asyncio.sleep(compute_delay(self._retry, attempt=attempt))
                    continue
                raise TBankNetworkError(str(exc)) from exc
            if response.status_code >= 400 and should_retry(
                self._retry, status=response.status_code, attempt=attempt
            ):
                await asyncio.sleep(
                    compute_delay(
                        self._retry,
                        attempt=attempt,
                        retry_after=self._retry_after(response),
                    )
                )
                continue
            return response

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncTransport":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()


class SyncTransport(_TransportBase):
    def __init__(self, *, client: Optional[httpx.Client] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client = client or httpx.Client(
            timeout=self._timeout, cert=self._cert, verify=self._verify
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Body = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Any] = None,
        content: Optional[Any] = None,
    ) -> httpx.Response:
        url = self._url(path)
        body, merged = self._prepare(json, headers)
        merged = _drop_json_content_type(merged, data, files)
        attempt = 0
        while True:
            attempt += 1
            try:
                response = self._client.request(
                    method,
                    url,
                    json=body,
                    params=params,
                    headers=merged,
                    data=data,
                    files=files,
                    content=content,
                )
            except httpx.TimeoutException as exc:
                if should_retry(self._retry, status=None, attempt=attempt):
                    time.sleep(compute_delay(self._retry, attempt=attempt))
                    continue
                raise TBankTimeoutError(str(exc)) from exc
            except httpx.HTTPError as exc:
                if should_retry(self._retry, status=None, attempt=attempt):
                    time.sleep(compute_delay(self._retry, attempt=attempt))
                    continue
                raise TBankNetworkError(str(exc)) from exc
            if response.status_code >= 400 and should_retry(
                self._retry, status=response.status_code, attempt=attempt
            ):
                time.sleep(
                    compute_delay(
                        self._retry,
                        attempt=attempt,
                        retry_after=self._retry_after(response),
                    )
                )
                continue
            return response

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SyncTransport":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
