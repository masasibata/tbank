from __future__ import annotations

from typing import Any, Dict

from tbank.core.errors import build_api_error


def raise_for_acquiring_result(data: Dict[str, Any]) -> None:
    """Бросает типизированное исключение, если ответ EACQ содержит ошибку."""
    if data.get("Success", True) and str(data.get("ErrorCode", "0")) == "0":
        return
    raise build_api_error(
        code=str(data.get("ErrorCode", "unknown")),
        message=data.get("Message") or "Acquiring request failed",
        details=data.get("Details"),
        status=data.get("Status"),
    )
