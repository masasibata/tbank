from __future__ import annotations

import httpx

from tbank.core.errors import TBankAPIError, error_from_tapi_response


def error_from_salary_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа зарплатного проекта."""
    return error_from_tapi_response(response, fallback="salary request failed")
