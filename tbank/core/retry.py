from __future__ import annotations

import random
from dataclasses import dataclass
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 8.0
    jitter: bool = True
    retry_statuses: FrozenSet[int] = frozenset({429, 500, 502, 503, 504})


def should_retry(policy: RetryPolicy, *, status: Optional[int], attempt: int) -> bool:
    """Ретраить ли попытку номер `attempt` (1-based)."""
    if attempt >= policy.attempts:
        return False
    if status is None:  # сетевая ошибка/таймаут
        return True
    return status in policy.retry_statuses


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
