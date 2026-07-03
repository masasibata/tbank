from __future__ import annotations

import httpx

from tbank.core.errors import TBankAPIError, TBankError, error_from_tapi_response


class CurrencySignatureRequiredError(TBankError):
    """Вызван подписанный метод, но клиент создан без ключа подписи (`signature`)."""


def error_from_ved_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа валютного контроля."""
    return error_from_tapi_response(response, fallback="ved request failed")
