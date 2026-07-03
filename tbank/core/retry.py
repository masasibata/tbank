from __future__ import annotations

import random
from dataclasses import dataclass
from typing import FrozenSet, Optional

# Методы, которые безопасно повторять: запрос можно отправить дважды
# без побочного эффекта (в отличие от POST-платежа).
IDEMPOTENT_METHODS: FrozenSet[str] = frozenset(
    {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}
)


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 8.0
    jitter: bool = True
    retry_statuses: FrozenSet[int] = frozenset({429, 500, 502, 503, 504})
    # True → ретраить и неидемпотентные запросы (POST без Idempotency-Key).
    # По умолчанию выключено: таймаут POST-платежа не означает, что платёж
    # не прошёл, и повтор может продублировать операцию.
    retry_non_idempotent: bool = False


def should_retry(
    policy: RetryPolicy,
    *,
    status: Optional[int],
    attempt: int,
    method: str = "GET",
    idempotent: Optional[bool] = None,
) -> bool:
    """Ретраить ли попытку номер `attempt` (1-based).

    `idempotent` — явный признак безопасности повтора (например, у запроса
    есть Idempotency-Key); если не задан, выводится из метода.
    429 повторяется всегда: сервер отклонил запрос до обработки.
    """
    if attempt >= policy.attempts:
        return False
    if idempotent is None:
        idempotent = method.upper() in IDEMPOTENT_METHODS
    safe = idempotent or policy.retry_non_idempotent
    if status is None:  # сетевая ошибка/таймаут
        return safe
    if status not in policy.retry_statuses:
        return False
    return safe or status == 429


def compute_delay(
    policy: RetryPolicy, *, attempt: int, retry_after: Optional[float] = None
) -> float:
    """Задержка перед попыткой `attempt` (1-based)."""
    if retry_after is not None:
        return min(retry_after, policy.backoff_max)
    delay = min(policy.backoff_base * (2.0 ** (attempt - 1)), policy.backoff_max)
    if policy.jitter:
        delay *= 0.5 + random.random() / 2
    return delay
