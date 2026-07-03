from __future__ import annotations

import httpx

from tbank.core.errors import TBankAPIError, error_from_tapi_response


def error_from_business_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа Т-Бизнеса."""
    return error_from_tapi_response(response, fallback="business request failed")
