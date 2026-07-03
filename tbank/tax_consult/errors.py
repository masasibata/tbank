from __future__ import annotations

from typing import Any, Dict, Type

import httpx

from tbank.core.errors import (
    AuthenticationError,
    ForbiddenError,
    InvalidRequestError,
    RateLimitError,
    ServerError,
    TBankAPIError,
    ValidationError,
)

_STATUS_MAP: Dict[int, Type[TBankAPIError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: InvalidRequestError,
    422: ValidationError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
}


def error_from_tax_consult_response(response: httpx.Response) -> TBankAPIError:
    """Исключение из T-API error-ответа ({errorId, errorMessage, errorCode,
    errorDetails})."""
    status = response.status_code
    try:
        raw = response.json()
    except ValueError:
        raw = None
    data: Dict[str, Any] = raw if isinstance(raw, dict) else {}

    code = str(data.get("errorCode") or status)
    message = data.get("errorMessage") or response.text or "tax-consult request failed"
    details = data.get("errorDetails")
    cls = _STATUS_MAP.get(status, TBankAPIError)
    return cls(
        code=code,
        message=message,
        http_status=status,
        error_id=data.get("errorId"),
        details=str(details) if details is not None else None,
    )
