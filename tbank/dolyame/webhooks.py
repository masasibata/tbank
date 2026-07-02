from __future__ import annotations

import ipaddress
from typing import Any, Dict

from tbank.dolyame.models import WebhookNotification

# Диапазон исходящих IP нотификаций Долями (для allowlist).
NOTIFICATION_NETWORK = ipaddress.ip_network("91.194.226.0/23")


def parse_notification(data: Dict[str, Any]) -> WebhookNotification:
    """Разобрать входящую нотификацию Долями в типизированную модель."""
    return WebhookNotification.model_validate(data)


def is_allowed_ip(ip: str) -> bool:
    """Проверить, что нотификация пришла из диапазона IP Долями (91.194.226.0/23)."""
    try:
        return ipaddress.ip_address(ip) in NOTIFICATION_NETWORK
    except ValueError:
        return False
