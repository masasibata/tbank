from __future__ import annotations

import httpx

from tbank.core.errors import TBankAPIError, error_from_tapi_response


def error_from_files_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа файлового хранилища."""
    return error_from_tapi_response(response, fallback="files request failed")
