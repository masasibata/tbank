from __future__ import annotations

from typing import Dict, Optional, Protocol, Tuple

Body = Optional[Dict[str, object]]
Headers = Dict[str, str]


class AuthStrategy(Protocol):
    """Готовит тело/заголовки запроса под конкретную схему auth."""

    def apply(self, body: Body, headers: Headers) -> Tuple[Body, Headers]: ...


class NoAuth:
    def apply(self, body: Body, headers: Headers) -> Tuple[Body, Headers]:
        return body, headers


class BearerAuth:
    def __init__(self, token: str) -> None:
        self._token = token

    def apply(self, body: Body, headers: Headers) -> Tuple[Body, Headers]:
        return body, {**headers, "Authorization": f"Bearer {self._token}"}
