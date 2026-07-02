# Долями (`tbank.dolyame`)

Оплата частями (BNPL) от Т-Банка: клиент платит 25% сразу и ещё 3 платежа по 25%
каждые 2 недели, а магазин получает всю сумму сразу после подтверждения.

- Хост: `https://partner.dolyame.ru/v1/` (demo-хост выдаётся при онбординге через `base_url`).
- Аутентификация: **mTLS-сертификат** (`cert`) + **HTTP Basic** (логин/пароль) +
  заголовок `X-Correlation-ID` (SDK генерирует сам).
- Суммы: **`Decimal` в рублях**.
- Провод: `snake_case` (совпадает с Python).
- Клиенты: `tbank.dolyame.DolyameClient` (async) и `tbank.dolyame.sync.DolyameClient` (sync).

## Жизненный цикл заказа

```python
from decimal import Decimal
from tbank.dolyame import DolyameClient
from tbank.dolyame.models import CreateOrderRequest, Order, Item, ClientInfo, CommitRequest

client = DolyameClient(
    login="shop", password="secret",
    cert=("client.pem", "client-key.pem"),   # mTLS-сертификат из ЛК (обязателен)
)

# 1) создать заказ → ссылка для клиента
info = await client.create_order(CreateOrderRequest(
    order=Order(id="order-1", amount=Decimal("6700.00"),
                items=[Item(name="Товар", quantity=1, price=Decimal("6700.00"))]),
    client_info=ClientInfo(first_name="Иван", phone="+79993334444"),
    notification_url="https://shop.example/webhook",
))
print(info.link)                              # клиент оформляет рассрочку здесь

# 2) статус, подтверждение, возврат, доставка:
info = await client.get_order("order-1")      # info.status, info.payment_schedule, ...
await client.commit("order-1", CommitRequest(
    amount=Decimal("6700.00"),
    items=[Item(name="Товар", quantity=1, price=Decimal("6700.00"))],
))
await client.cancel("order-1")
# refund / correction / complete_delivery — см. справочник клиента ниже
```

## Вебхуки

Долями шлёт нотификации POST на `notification_url`. Проверяйте, что запрос пришёл
из диапазона IP Долями, и перепроверяйте статус через `get_order`:

```python
from tbank.dolyame.webhooks import parse_notification, is_allowed_ip

if not is_allowed_ip(request_remote_ip):     # диапазон 91.194.226.0/23
    return
note = parse_notification(await request.json())
if note.status is OrderStatus.COMMITTED:
    ...
```

:::{note}
Точный алгоритм подписи `signature` в публичной доке не формализован — полагайтесь
на allowlist IP и перезапрос статуса через `get_order`.
:::

## Клиент

```{eval-rst}
.. autoclass:: tbank.dolyame.aio.DolyameClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.dolyame.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.dolyame.enums
   :members:
   :undoc-members:
```
