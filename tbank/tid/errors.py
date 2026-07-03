from __future__ import annotations

from typing import Any, Dict

import httpx

from tbank.core.errors import (
    STATUS_ERROR_MAP,
    AuthenticationError,
    ForbiddenError,
    TBankAPIError,
    ValidationError,
    error_from_tapi_response,
)


def error_from_tid_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа data-эндпоинтов T-ID
    ({errorId, errorMessage, errorCode, errorDetails})."""
    return error_from_tapi_response(response, fallback="T-ID request failed")


def error_from_oauth_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из OAuth error-ответа id.tbank.ru
    ({error, error_description, error_uri}, RFC 6749 §5.2)."""
    status = response.status_code
    try:
        raw = response.json()
    except ValueError:
        raw = None
    data: Dict[str, Any] = raw if isinstance(raw, dict) else {}

    code = str(data.get("error") or status)
    message = data.get("error_description") or response.text or "OAuth request failed"
    details = data.get("error_uri")
    # invalid_client → 401 в теле часто с 400: приоритезируем текстовый код.
    cls = STATUS_ERROR_MAP.get(status, TBankAPIError)
    if code in ("invalid_client", "unauthorized_client", "access_denied"):
        cls = AuthenticationError if code == "invalid_client" else ForbiddenError
    elif code in ("invalid_request", "invalid_grant", "unsupported_grant_type"):
        cls = ValidationError
    return cls(
        code=code,
        message=message,
        http_status=status,
        details=str(details) if details is not None else None,
    )
