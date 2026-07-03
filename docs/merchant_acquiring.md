# Торговый эквайринг (`tbank.merchant_acquiring`)

Отчётность по торговому (POS) эквайрингу: список подключённых терминалов и
операции по ним. Это отдельный API от интернет-эквайринга
([`tbank.acquiring`](acquiring.md)).

- Хост: `business.tbank.ru/openapi` по **Bearer**-токену.
- Суммы: **в копейках** (`int`). Провод: `camelCase`.
- Клиенты: `tbank.merchant_acquiring.MerchantAcquiringClient` (async) и
  `tbank.merchant_acquiring.sync.MerchantAcquiringClient` (sync).

```python
from tbank.merchant_acquiring import MerchantAcquiringClient

client = MerchantAcquiringClient(token="business-token")

# терминалы (постранично)
page = await client.list_terminals(page=0, size=50)
for terminal in page.terminals or []:
    print(terminal.key)

# операции по терминалу за период
ops = await client.list_operations(
    terminal_key="TERM1", from_date="2026-01-01", till="2026-01-31", limit=100,
)
for op in ops.operations or []:
    print(op.transaction_date, op.amount, op.type)   # amount — в копейках
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.merchant_acquiring.aio.MerchantAcquiringClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.merchant_acquiring.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.merchant_acquiring.enums
   :members:
   :undoc-members:
```
