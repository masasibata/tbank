from __future__ import annotations

import httpx

from tbank.core.errors import TBankAPIError, error_from_tapi_response


def error_from_self_employed_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа выплат самозанятым."""
    return error_from_tapi_response(response, fallback="self-employed request failed")
