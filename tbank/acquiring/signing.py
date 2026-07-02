from __future__ import annotations

import hashlib
from typing import Any, Dict


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_token(fields: Dict[str, Any], password: str) -> str:
    """SHA-256-подпись запроса эквайринга.

    Берём только корневые скалярные поля (вложенные объекты/массивы и None —
    исключаются, поле Token игнорируется), добавляем Password, сортируем по
    ключу, конкатенируем значения, считаем SHA-256 (UTF-8).
    """
    payload: Dict[str, Any] = {
        key: value
        for key, value in fields.items()
        if key != "Token" and value is not None and not isinstance(value, (dict, list))
    }
    payload["Password"] = password
    concatenated = "".join(_stringify(payload[key]) for key in sorted(payload))
    return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()
