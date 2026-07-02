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

with AcquiringClient(terminal_key="...", password="...") as client:
    payment = client.init(InitRequest(amount=150000, order_id="A-1"))
```

## Открытый банк — счета и выписки

```python
from datetime import datetime, timezone
from tbank.business import BusinessClient
from tbank.business.models import StatementParams


async def main() -> None:
    client = BusinessClient(token="...")          # self-service токен из ЛК
    accounts = await client.get_accounts()        # счета + балансы (Decimal)
    params = StatementParams(
        account_number="40802...",
        from_=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    async for op in client.iter_statement(params):  # авто-пагинация по nextCursor
        print(op.operation_id, op.operation_amount)
    await client.aclose()
```

## Рублёвый платёж через mTLS

```python
from decimal import Decimal
from tbank.business import BusinessClient
from tbank.business.models import CreatePaymentRequest, PaymentFrom, ReceiverRequisites

client = BusinessClient(token="...", cert=("client.pem", "key.pem"))
pid = await client.create_ruble_payment(
    CreatePaymentRequest(
        from_=PaymentFrom(account_number="40802..."),
        to=ReceiverRequisites(
            name="ООО Ромашка", inn="7700000000",
            account_number="40702...", bik="044525974",
        ),
        purpose="Оплата по счёту 1",
        amount=Decimal("12345.67"),
    )
)
```

## Обработка ошибок

```python
from tbank.core.errors import TBankAPIError, TBankNetworkError, InsufficientFundsError

try:
    await client.charge(payment_id, rebill_id)
except InsufficientFundsError:
    ...
except TBankAPIError as exc:
    print(exc.code, exc.message)
except TBankNetworkError:
    ...
```
