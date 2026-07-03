from __future__ import annotations

from enum import Enum


class EtpArrestStatus(str, Enum):
    """Статус картотеки ЭТП / ареста на специальном счёте."""

    PAYED = "PAYED"
    ACTIVE = "ACTIVE"
    PAUSE = "PAUSE"
    CANCELED = "CANCELED"
