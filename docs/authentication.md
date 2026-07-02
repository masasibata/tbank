# Аутентификация

У продуктов Т-Банка три разные схемы аутентификации — SDK берёт их на себя.

## Эквайринг — Token-подпись (SHA-256)

Эквайринг подписывает каждый запрос: SDK берёт корневые поля тела, добавляет
`Password`, сортирует по ключу, конкатенирует значения и считает `SHA-256`.
Вложенные объекты (`Receipt`, `Items`, ...) в подпись **не** входят. Тебе достаточно
передать `terminal_key` и `password` из ЛК:

```python
from tbank.acquiring import AcquiringClient

client = AcquiringClient(terminal_key="TinkoffMerchantKey", password="password123")
```

Тот же алгоритм используется для проверки подписи входящих вебхуков — см.
[Вебхуки](webhooks.md).

## Открытый банк — Bearer-токен

Для чтения (счета, выписки) и части операций достаточно self-service токена из
ЛК Т-Бизнеса (Интеграции → T-API → «Выпустить токен», с привязкой IP):

```python
from tbank.business import BusinessClient

client = BusinessClient(token="t.xxxxxxxx")
```

## Открытый банк — mTLS

Операции движения денег (например `create_ruble_payment`) идут на защищённый хост
`secured-openapi.tbank.ru` и требуют **взаимного TLS** — клиентского сертификата
из ЛК. Передай его в `cert` (и при необходимости CA-бандл в `verify`):

```python
client = BusinessClient(
    token="t.xxxxxxxx",
    cert=("client.pem", "client-key.pem"),   # или один combined .pem
)
```

:::{note}
mTLS настраивается на транспорте, а не в заголовке: при рукопожатии банк
криптографически проверяет, что соединение установил именно твой сервер.
Без сертификата secured-метод поднимет `MutualTLSRequiredError`.
:::

Read-методы (счета/выписки) работают и без сертификата — он нужен только для
защищённых операций.
