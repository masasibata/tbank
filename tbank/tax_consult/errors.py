from __future__ import annotations

import httpx

from tbank.core.errors import TBankAPIError, error_from_tapi_response


def error_from_tax_consult_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа налоговых консультаций."""
    return error_from_tapi_response(response, fallback="tax-consult request failed")
