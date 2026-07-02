# Открытый банк (`tbank.business`)

Открытый банковский API Т-Бизнеса (T-API): счета и выписки, рублёвые платежи,
инвойсы, СБП-ссылки.

- Хосты: `https://business.tbank.ru/openapi` (чтение),
  `https://secured-openapi.tbank.ru` (движение денег, mTLS); `sandbox=True` — песочница.
- Аутентификация: [Bearer и mTLS](authentication.md)
- Суммы: **`Decimal` в рублях**
- Клиенты: `tbank.business.BusinessClient` (async) и
  `tbank.business.sync.BusinessClient` (sync).

## Счета и выписки

```python
from datetime import datetime, timezone
from tbank.business import BusinessClient
from tbank.business.models import StatementParams, BankStatementParams
from datetime import date

client = BusinessClient(token="...")

accounts = await client.get_accounts()                 # счета + балансы

# выписка операций с курсорной авто-пагинацией:
params = StatementParams(account_number="40802...",
                         from_=datetime(2026, 1, 1, tzinfo=timezone.utc))
async for op in client.iter_statement(params):
    print(op.operation_id, op.operation_amount)

# одна страница или выписка за период:
page = await client.get_statement(params)              # page.operations, page.next_cursor
stmt = await client.get_bank_statement(
    BankStatementParams(account_number="40802...", from_=date(2026, 1, 1), till=date(2026, 1, 31))
)
```

## Рублёвый платёж (mTLS)

```python
from decimal import Decimal
from tbank.business.models import (
    CreatePaymentRequest, PaymentFrom, ReceiverRequisites, TaxPaymentParameters,
)

client = BusinessClient(token="...", cert=("client.pem", "key.pem"))

pid = await client.create_ruble_payment(CreatePaymentRequest(
    from_=PaymentFrom(account_number="40802..."),
    to=ReceiverRequisites(name="ООО Ромашка", inn="7700000000",
                          account_number="40702...", bik="044525974"),
    purpose="Оплата по счёту 1", amount=Decimal("12345.67"),
    # tax=TaxPaymentParameters(...) — для налогов/взносов
))
status = await client.get_payment_status(pid)          # mTLS
await client.get_documents_status([pid])               # батч-статусы (обычный хост)
```

:::{note}
`id` платежа — ключ идемпотентности; если не передать, генерируется автоматически.
:::

## Инвойсы и СБП-ссылки

```python
from decimal import Decimal
from tbank.business.models import SendInvoiceRequest, InvoiceItem, CreateOnetimeQrRequest

inv = await client.send_invoice(SendInvoiceRequest(
    invoice_number="101",
    items=[InvoiceItem(name="Товар", price=Decimal("100.50"), unit="шт",
                       vat="20", amount=Decimal("2"))],
))
await client.get_invoice_info(inv.invoice_id)          # DRAFT / SUBMITTED / EXECUTED

qr = await client.create_onetime_qr(
    CreateOnetimeQrRequest(sum=Decimal("1500.00"), purpose="Оплата", ttl=3)
)
print(qr.payment_url)
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.business.aio.BusinessClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.business.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.business.enums
   :members:
   :undoc-members:
```
