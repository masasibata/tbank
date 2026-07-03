"""Общие адреса хостов открытого банка T-API.

Единственный источник: домены импортируют константы отсюда,
а не объявляют свои копии.
"""

from __future__ import annotations

PROD_URL = "https://business.tbank.ru/openapi"
SANDBOX_URL = "https://business.tbank.ru/openapi/sandbox"
SECURED_URL = "https://secured-openapi.tbank.ru"
SANDBOX_SECURED_URL = "https://business.tbank.ru/openapi/sandbox/secured"
