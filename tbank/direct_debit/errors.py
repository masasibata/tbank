from __future__ import annotations

import httpx

from tbank.core.errors import TBankAPIError, error_from_tapi_response


def error_from_direct_debit_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа безакцептных списаний."""
    return error_from_tapi_response(response, fallback="direct-debit request failed")
