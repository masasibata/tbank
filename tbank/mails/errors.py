from __future__ import annotations

import httpx

from tbank.core.errors import TBankAPIError, TBankError, error_from_tapi_response


class MailSignatureRequiredError(TBankError):
    """Вызван `push_incoming_mail`, но клиент создан без ключа подписи."""


def error_from_mails_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа внутренних писем."""
    return error_from_tapi_response(response, fallback="mails request failed")
