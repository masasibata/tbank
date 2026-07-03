from __future__ import annotations

import httpx

from tbank.core.errors import TBankAPIError, error_from_tapi_response


def error_from_overnight_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа овернайта."""
    return error_from_tapi_response(response, fallback="overnight request failed")
