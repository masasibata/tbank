"""Парсеры бизнес-карт (общие для sync- и aio-клиентов)."""

from __future__ import annotations

from typing import List

from pydantic import TypeAdapter

from tbank.business_cards.models import VirtualCardApplication

APPLICATIONS: TypeAdapter[List[VirtualCardApplication]] = TypeAdapter(
    List[VirtualCardApplication]
)
