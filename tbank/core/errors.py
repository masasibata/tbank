from __future__ import annotations

from typing import Dict, Optional, Type


class TBankError(Exception):
    """Базовое исключение SDK."""


class TBankNetworkError(TBankError):
    """Сетевой сбой (соединение/таймаут) после исчерпания ретраев."""


class TBankTimeoutError(TBankNetworkError):
    """Истёк таймаут запроса."""


class MutualTLSRequiredError(TBankError):
    """Вызван secured-метод, но клиент создан без mTLS-сертификата."""


class TBankAPIError(TBankError):
    """Логическая ошибка API (Success=false / HTTP 4xx-5xx)."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: Optional[str] = None,
        http_status: Optional[int] = None,
        status: Optional[str] = None,
        error_id: Optional[str] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        self.http_status = http_status
        self.status = status
        self.error_id = error_id
        text = f"[{code}] {message}"
        if details:
            text += f" ({details})"
        super().__init__(text)


class AuthenticationError(TBankAPIError):
    """Ошибка аутентификации/подписи."""


class InvalidRequestError(TBankAPIError):
    """Некорректный запрос/параметры."""


class InsufficientFundsError(TBankAPIError):
    """Недостаточно средств на карте."""


class ThreeDSError(TBankAPIError):
    """Не пройдена аутентификация 3DS."""


class TerminalBlockedError(TBankAPIError):
    """Операция заблокирована для терминала."""


class ForbiddenError(TBankAPIError):
    """Доступ запрещён (неизвестный IP / нехватка скоупов / нет прав). HTTP 403."""


class ValidationError(TBankAPIError):
    """Некорректные данные запроса. HTTP 400/422."""


class RateLimitError(TBankAPIError):
    """Превышен лимит запросов. HTTP 429."""


class ServerError(TBankAPIError):
    """Ошибка на стороне сервера. HTTP 5xx."""


# EACQ ErrorCode -> класс исключения (сверять с mapi_errors_list.pdf при расширении).
ERROR_REGISTRY: Dict[str, Type[TBankAPIError]] = {
    "10": TerminalBlockedError,
    "101": ThreeDSError,
    "1051": InsufficientFundsError,
}


def build_api_error(
    *,
    code: str,
    message: str,
    details: Optional[str] = None,
    http_status: Optional[int] = None,
    status: Optional[str] = None,
) -> TBankAPIError:
    """Собрать типизированное исключение по коду ошибки."""
    cls = ERROR_REGISTRY.get(code, TBankAPIError)
    return cls(
        code=code,
        message=message,
        details=details,
        http_status=http_status,
        status=status,
    )
