# Вебхуки (эквайринг)

Т-Банк отправляет уведомления о платежах POST-запросом на `NotificationURL`.
Обработчик должен проверить подпись и вернуть `HTTP 200` с телом ровно `OK`.

## Разбор и проверка

```python
from tbank.acquiring.webhooks import parse_notification, verify_notification

async def handler(request):
    data = await request.json()

    if not verify_notification(data, password="password123"):
        return  # подпись не сошлась — отклоняем

    note = parse_notification(data)          # типизированная модель
    if note.status is PaymentStatus.CONFIRMED:
        ...                                  # платёж подтверждён
        # для рекуррента сохраните note.rebill_id
    return "OK"
```

- `verify_notification(data, password)` — проверяет `Token` тем же алгоритмом
  SHA-256, что и подпись запросов (см. [Аутентификация](authentication.md)).
- `parse_notification(data)` → `PaymentNotification`
  (`terminal_key`, `order_id`, `success`, `status`, `payment_id`, `amount`,
  `card_id`, `pan`, `rebill_id`, ...).

:::{tip}
Для родительского рекуррентного платежа `RebillId` приходит именно в вебхуке на
статус `AUTHORIZED` — сохраните его для последующих `charge(...)`.
:::

## Справочник

```{eval-rst}
.. automodule:: tbank.acquiring.webhooks
   :members:
```
