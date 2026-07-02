# Обработка ошибок

Все исключения наследуются от `tbank.core.errors.TBankError`.

```
TBankError
├── TBankNetworkError            сеть/соединение после ретраев
│   └── TBankTimeoutError        таймаут
├── MutualTLSRequiredError       secured-метод вызван без mTLS-сертификата
└── TBankAPIError                логическая ошибка API (code/message/http_status)
    ├── AuthenticationError
    ├── InvalidRequestError
    ├── ValidationError
    ├── ForbiddenError
    ├── RateLimitError
    ├── ServerError
    ├── InsufficientFundsError
    ├── ThreeDSError
    └── TerminalBlockedError
```

## Пример

```python
from tbank.core.errors import (
    TBankAPIError,
    TBankNetworkError,
    InsufficientFundsError,
)

try:
    await client.charge(payment_id, rebill_id)
except InsufficientFundsError:
    ...                              # недостаточно средств (эквайринг, код 1051)
except TBankAPIError as exc:
    print(exc.code, exc.message, exc.http_status)
except TBankNetworkError:
    ...                              # сеть/таймаут после исчерпания ретраев
```

## Как это устроено

- **Эквайринг** возвращает ошибку в теле ответа (`Success=false`, `ErrorCode`)
  даже при HTTP 200 — SDK маппит `ErrorCode` в типизированное исключение
  (например `1051` → `InsufficientFundsError`).
- **Открытый банк** возвращает ошибку через HTTP-код и тело
  `{errorId, errorMessage, errorCode, errorDetails}` — SDK маппит статус в класс
  (`403` → `ForbiddenError`, `429` → `RateLimitError`, `5xx` → `ServerError`).

У `TBankAPIError` доступны атрибуты: `code`, `message`, `details`, `http_status`,
`status`, `error_id`.

Полный справочник — в разделе [Ядро](core.md).
