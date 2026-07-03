from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx
from pydantic import TypeAdapter

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.signing import HttpSignature
from tbank.core.transport import SyncTransport
from tbank.mails.errors import (
    MailSignatureRequiredError,
    error_from_mails_response,
)
from tbank.mails.models import (
    IncomingMailRequest,
    IncomingMailResult,
    Mail,
    MarkReadRequest,
)

SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"

_BASE = "/api/internal/v1/mails"
_INCOMING = f"{_BASE}/incoming"
_READ = f"{_BASE}/read"
_UNREAD = f"{_BASE}/unread"

_UNREAD_LIST: TypeAdapter[List[Mail]] = TypeAdapter(List[Mail])


class MailsClient(BaseSyncClient):
    """Синхронный клиент внутренних писем (H2H): входящие письма, отметка о
    прочтении, непрочитанные письма.

    Домен работает на secured-хосте (**mTLS**, `cert`). Отправка входящего письма
    дополнительно подписывается (`signature` — `HttpSignature(keyId, secret)`);
    остальные методы — по **Bearer**. Провод — `camelCase`.
    """

    def __init__(
        self,
        token: str,
        *,
        signature: Optional[HttpSignature] = None,
        base_url: Optional[str] = None,
        sandbox: bool = False,
        cert: Optional[Any] = None,
        verify: Any = True,
        retry: Optional[RetryPolicy] = None,
        transport: Optional[SyncTransport] = None,
    ) -> None:
        self._signature = signature
        resolved = base_url or (SANDBOX_SECURED_URL if sandbox else SECURED_URL)
        transport = transport or SyncTransport(
            base_url=resolved,
            auth=BearerAuth(token),
            cert=cert,
            verify=verify,
            retry=retry,
        )
        super().__init__(transport)

    def _error_from_response(self, response: httpx.Response) -> TBankAPIError:
        return error_from_mails_response(response)

    def push_incoming_mail(self, request: IncomingMailRequest) -> IncomingMailResult:
        """Отправить входящее письмо (mTLS + подпись)."""
        if self._signature is None:
            raise MailSignatureRequiredError(
                "Метод требует подпись: передайте signature=HttpSignature(...)."
            )
        body = _body_bytes(request)
        headers = {
            "Content-Type": "application/json",
            **self._signature.build_headers("POST", _INCOMING, body),
        }
        response = self._transport.request(
            "POST", _INCOMING, content=body, headers=headers
        )
        self._raise_for_http(response)
        return IncomingMailResult.model_validate(self._parse_body(response))

    def mark_read(self, request: MarkReadRequest) -> None:
        """Отметить сообщения как прочитанные."""
        response = self._transport.request("POST", _READ, json=_dump(request))
        self._raise_for_http(response)

    def list_unread(self) -> List[Mail]:
        """Непрочитанные письма со списком сообщений."""
        response = self._transport.request("GET", _UNREAD)
        self._raise_for_http(response)
        return _UNREAD_LIST.validate_python(self._parse_body(response))


def _dump(request: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = request.model_dump(
        by_alias=True, exclude_none=True, mode="json"
    )
    return result


def _body_bytes(request: Any) -> bytes:
    return json.dumps(_dump(request), ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
