from __future__ import annotations

from tbank.core.signing import DEFAULT_SIGNED_HEADERS, HttpSignature

# Валютный контроль подписывает запросы обобщённой HTTP-подписью (draft-cavage).
CurrencySignature = HttpSignature

__all__ = ["CurrencySignature", "DEFAULT_SIGNED_HEADERS"]
