# Овернайты (`tbank.overnight`)

Овернайт — размещение свободного остатка расчётного счёта на ночь под процент.
SDK покрывает сводку по счёту и пополнение.

- Хост: `secured-openapi.tbank.ru`, требуется **mTLS-сертификат** (`cert`).
- Суммы T-API отдаёт **строками** — модели сохраняют их как есть (без `Decimal`).
- Клиенты: `tbank.overnight.OvernightClient` (async) и
  `tbank.overnight.sync.OvernightClient` (sync).

```python
from tbank.overnight import OvernightClient

client = OvernightClient(
    token="business-token",
    cert=("client.pem", "client-key.pem"),
)

info = await client.get_overnight_info("OV-АГ-123")
print(info.amount, info.percent_rate)         # сумма на счёте, ставка
print(info.auto_pay.is_active)                # автоматическое размещение
print(info.actual_deal.paid_amount)           # будущая выплата по сделке

await client.replenish_overnight("OV-АГ-123", "50000.00")
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.overnight.aio.OvernightClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.overnight.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.overnight.enums
   :members:
   :undoc-members:
```
