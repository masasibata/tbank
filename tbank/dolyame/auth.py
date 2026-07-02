from __future__ import annotations

import base64
import uuid
from typing import Dict, Optional, Tuple

Body = Optional[Dict[str, object]]
Headers = Dict[str, str]


class DolyameAuth:
    """Долями: HTTP Basic + свежий X-Correlation-ID (UUID v4) на каждый запрос.

    mTLS-сертификат настраивается отдельно на транспорте (`cert=`).
    """

    def __init__(self, login: str, password: str) -> None:
        token = base64.b64encode(f"{login}:{password}".encode("utf-8")).decode("ascii")
        self._header = f"Basic {token}"

    def apply(self, body: Body, headers: Headers) -> Tuple[Body, Headers]:
        return body, {
            **headers,
            "Authorization": self._header,
            "X-Correlation-ID": str(uuid.uuid4()),
        }
