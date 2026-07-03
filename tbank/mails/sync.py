from __future__ import annotations

from typing import List, Optional

import httpx

from tbank.core.auth import BearerAuth
from tbank.core.client import BaseSyncClient
from tbank.core.errors import TBankAPIError
from tbank.core.retry import RetryPolicy
from tbank.core.signing import HttpSignature
from tbank.core.transport import CertTypes, SyncTransport, VerifyTypes
from tbank.core.urls import SANDBOX_SECURED_URL, SECURED_URL
from tbank.mails import _endpoints
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
        cert: Optional[CertTypes] = None,
        verify: VerifyTypes = True,
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
        body = _endpoints.body_bytes(request)
        headers = {
            "Content-Type": "application/json",
            **self._signature.build_headers("POST", _endpoints.INCOMING, body),
        }
        response = self._transport.request(
            "POST", _endpoints.INCOMING, content=body, headers=headers
        )
        self._raise_for_http(response)
        return IncomingMailResult.model_validate(self._parse_body(response))

    def mark_read(self, request: MarkReadRequest) -> None:
        """Отметить сообщения как прочитанные."""
        self._send("POST", _endpoints.READ, body=request)

    def list_unread(self) -> List[Mail]:
        """Непрочитанные письма со списком сообщений."""
        return self._get(_endpoints.UNREAD, _endpoints.UNREAD_LIST)
