"""Пути API торгового эквайринга (общие для sync- и aio-клиентов)."""

from __future__ import annotations

TERMINALS = "/api/v1/tacq/terminals"


def operations_path(terminal_key: str) -> str:
    return f"/api/v1/tacq/operations/terminal/{terminal_key}"
