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
    400: InvalidRequestError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: InvalidRequestError,
    409: InvalidRequestError,
    422: ValidationError,
    429: RateLimitError,
    500: ServerError,
}


def error_from_dolyame_response(response: httpx.Response) -> TBankAPIError:
    """Строит типизированное исключение из error-ответа Долями
    ({code, message, errorDetailCode, correlationId})."""
    status = response.status_code
    try:
        raw = response.json()
    except ValueError:
        raw = None
    data: Dict[str, Any] = raw if isinstance(raw, dict) else {}

    code = str(data.get("code") or status)
    message = data.get("message") or response.text or "Dolyame request failed"
    detail = data.get("errorDetailCode") or data.get("details")
    cls = _STATUS_MAP.get(status, TBankAPIError)
    return cls(
        code=code,
        message=message,
        http_status=status,
        error_id=data.get("correlationId"),
        details=str(detail) if detail is not None else None,
    )
