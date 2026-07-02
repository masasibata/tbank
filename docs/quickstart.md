# Быстрый старт

## Эквайринг — приём платежа

```python
import asyncio
from tbank.acquiring import AcquiringClient
from tbank.acquiring.models import InitRequest


async def main() -> None:
    async with AcquiringClient(terminal_key="...", password="...") as client:
        payment = await client.init(InitRequest(amount=150000, order_id="A-1"))
        print(payment.payment_url)          # редиректим покупателя сюда
        state = await client.get_state(payment.payment_id)
        print(state.status)


asyncio.run(main())
```

Синхронный клиент — тот же API без `async`/`await`:

```python
from tbank.acquiring.sync import AcquiringClient
from tbank.acquiring.models import InitRequest

with AcquiringClient(terminal_key="...", password="...") as client:
    payment = client.init(InitRequest(amount=150000, order_id="A-1"))
```

:::{tip}
Суммы в эквайринге — **в копейках** (`int`): `150000` = 1500 ₽.
:::

## Открытый банк — счета и выписки

```python
from datetime import datetime, timezone
from tbank.business import BusinessClient
from tbank.business.models import StatementParams


async def main() -> None:
    client = BusinessClient(token="...")          # self-service токен из ЛК
    for acc in await client.get_accounts():       # счета + балансы (Decimal)
        print(acc.account_number, acc.balance.otb if acc.balance else None)

    params = StatementParams(
        account_number="40802...",
        from_=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    async for op in client.iter_statement(params):  # авто-пагинация по nextCursor
        print(op.operation_id, op.operation_amount)
    await client.aclose()
```

:::{tip}
Суммы в открытом банке — **`Decimal` в рублях** (без float-погрешности).
:::

## Что дальше

- [Аутентификация](authentication.md) — Token-подпись, Bearer, mTLS.
- [Обработка ошибок](errors.md) — иерархия исключений.
- [Эквайринг](acquiring.md) и [Открытый банк](business.md) — полный справочник методов.
