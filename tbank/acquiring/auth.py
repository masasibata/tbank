from __future__ import annotations

from typing import Dict, Optional, Tuple

from tbank.acquiring.signing import build_token

Body = Optional[Dict[str, object]]
Headers = Dict[str, str]


class TokenSignatureAuth:
    """EACQ: добавляет TerminalKey и SHA-256 Token в тело запроса."""

    def __init__(self, terminal_key: str, password: str) -> None:
        self._terminal_key = terminal_key
        self._password = password

    def apply(self, body: Body, headers: Headers) -> Tuple[Body, Headers]:
        payload: Dict[str, object] = dict(body or {})
        payload["TerminalKey"] = self._terminal_key
        payload["Token"] = build_token(payload, self._password)
        return payload, headers
