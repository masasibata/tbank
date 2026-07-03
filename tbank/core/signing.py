from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence

# Заголовки, подписываемые по умолчанию (порядок важен для строки подписи).
DEFAULT_SIGNED_HEADERS: Sequence[str] = ("(request-target)", "date", "data")


def _hmac_b64(secret: str, message: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class HttpSignature:
    """Подпись запросов по схеме HTTP Signatures (draft-cavage), HMAC-SHA256.

    `keyId` и секрет выдаёт менеджер Т-Банка. Используется валютным контролем
    (`tbank.ved`) и внутренними письмами (`tbank.mails`).

    .. warning::
       Точная сборка строки подписи в OpenAPI-спеке приведена не полностью
       (нет примера). Реализация следует стандарту draft-cavage: строка подписи —
       это построчное объединение подписываемых заголовков (`name: value`), где
       `(request-target)` = ``<method> <path>?<query>``. Перед боевым использованием
       сверьте с реальным ключом.
    """

    def __init__(
        self,
        key_id: str,
        secret: str,
        *,
        signed_headers: Sequence[str] = DEFAULT_SIGNED_HEADERS,
    ) -> None:
        self._key_id = key_id
        self._secret = secret
        self._signed_headers = tuple(signed_headers)

    def request_target(self, method: str, path: str, query: str = "") -> str:
        return f"{method.lower()} {path}?{query}"

    def build_headers(
        self,
        method: str,
        path: str,
        body: bytes,
        *,
        query: str = "",
        date: Optional[str] = None,
    ) -> Dict[str, str]:
        """Заголовки `date`, `data` и `Signature` для подписанного запроса."""
        date = date or _now_iso()
        data = _hmac_b64(self._secret, body)
        target = self.request_target(method, path, query)
        values = {"date": date, "data": data}
        lines = []
        for name in self._signed_headers:
            if name == "(request-target)":
                lines.append(f"(request-target): {target}")
            else:
                lines.append(f"{name}: {values[name]}")
        signature = _hmac_b64(self._secret, "\n".join(lines).encode("utf-8"))
        header = (
            f'Signature keyId="{self._key_id}",algorithm="HMAC-SHA256",'
            f'headers="{" ".join(self._signed_headers)}",signature="{signature}"'
        )
        return {"date": date, "data": data, "Signature": header}
