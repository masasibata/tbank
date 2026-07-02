# tbank

[![PyPI](https://img.shields.io/pypi/v/tbank.svg)](https://pypi.org/project/tbank/)
[![Python](https://img.shields.io/pypi/pyversions/tbank.svg)](https://pypi.org/project/tbank/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](#-разработка)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue.svg)](#-разработка)

**Асинхронный и синхронный Python SDK для API Т-Банка (ex-Тинькофф).**

`tbank` — типизированная библиотека для интеграции с платёжными и банковскими сервисами Т-Банка: интернет-эквайринг (приём платежей, СБП, рекуррент, фискализация 54-ФЗ) и открытый банковский API Т-Бизнеса (счета, выписки, рублёвые платежи, инвойсы, СБП-ссылки). Один пакет — оба мира, с общим ядром.

## ✨ Особенности

- 🚀 **Async и sync** — один API в двух вариантах на общем ядре (`httpx`).
- 🛡️ **Строгая типизация** — pydantic v2, `mypy --strict` без ошибок, `py.typed`.
- 🔌 **Полное покрытие** — эквайринг (EACQ) и открытый банк (T-API) в одном пакете.
- 🔐 **Аутентификация из коробки** — SHA-256 Token-подпись (эквайринг), Bearer и **mTLS** (открытый банк).
- 💸 **Корректные деньги** — копейки (`int`) для эквайринга, `Decimal` для открытого банка (без float-погрешности).
- 🔁 **Надёжность** — ретраи с экспоненциальным бэкоффом, уважение `Retry-After`, идемпотентность.
- 🧪 **Проверено** — 111 тестов, 99% покрытие.

## 📦 Установка

```bash
pip install tbank
```

Зависимости: Python 3.9+, `pydantic>=2`, `httpx`.

## 🚀 Быстрый старт

### Эквайринг — приём платежа (redirect)

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

Синхронный вариант — тот же API без `async`/`await`:

```python
from tbank.acquiring.sync import AcquiringClient

with AcquiringClient(terminal_key="...", password="...") as client:
    payment = client.init(InitRequest(amount=150000, order_id="A-1"))
```

### Открытый банк — счета и выписки

```python
from decimal import Decimal
from tbank.business import BusinessClient
from tbank.business.models import StatementParams
from datetime import datetime, timezone


async def main() -> None:
    client = BusinessClient(token="...")             # self-service токен из ЛК
    accounts = await client.get_accounts()           # счета + балансы (Decimal)
    async for op in client.iter_statement(
        StatementParams(account_number="40802...", from_=datetime(2026, 1, 1, tzinfo=timezone.utc))
    ):
        print(op.operation_id, op.operation_amount)  # авто-пагинация по nextCursor
    await client.aclose()
```

## 🧩 Что покрыто

| Домен | Возможности |
| --- | --- |
| **`tbank.acquiring`** (EACQ) | Приём платежей (`init`/`get_state`/`confirm`/`cancel`), вебхуки, рекуррент (`charge`), клиенты и карты (`add_customer`/`get_card_list`/`remove_card`), СБП QR (`get_qr`/`get_qr_members`) и СБП-рекуррент (`add_account_qr`/`charge_qr`), фискализация 54-ФЗ (`Receipt`/`send_closing_receipt`), привязка карт (`add_card`/`get_add_card_state`) |
| **`tbank.business`** (T-API) | Счета и балансы (`get_accounts`), выписки с курсорной авто-пагинацией (`get_statement`/`iter_statement`/`get_bank_statement`), рублёвые платежи с налоговым блоком через **mTLS** (`create_ruble_payment`/`get_payment_status`), инвойсы (`send_invoice`), СБП-ссылки b2b (`create_onetime_qr`/`create_reusable_qr`) |

## 📋 Примеры

<details>
<summary>Рекуррентный платёж (эквайринг)</summary>

```python
# 1) при первом платеже сохраняем карту:
await client.init(InitRequest(amount=150000, order_id="A-1", customer_key="c1", recurrent="Y"))
# → RebillId приходит в вебхуке на статус AUTHORIZED

# 2) последующие списания без покупателя:
await client.charge(payment_id, rebill_id)
```
</details>

<details>
<summary>СБП QR (эквайринг)</summary>

```python
from tbank.acquiring.enums import QrDataType

payment = await client.init(InitRequest(amount=150000, order_id="A-1"))
qr = await client.get_qr(payment.payment_id, data_type=QrDataType.PAYLOAD)
print(qr.data)                                  # ссылка qr.nspk.ru
```
</details>

<details>
<summary>Рублёвый платёж с mTLS (открытый банк)</summary>

```python
from decimal import Decimal
from tbank.business import BusinessClient
from tbank.business.models import CreatePaymentRequest, PaymentFrom, ReceiverRequisites

client = BusinessClient(token="...", cert=("client.pem", "key.pem"))  # mTLS-сертификат из ЛК
pid = await client.create_ruble_payment(CreatePaymentRequest(
    from_=PaymentFrom(account_number="40802..."),
    to=ReceiverRequisites(name="ООО Ромашка", inn="7700000000", account_number="40702...", bik="044525974"),
    purpose="Оплата по счёту 1", amount=Decimal("12345.67"),
))
status = await client.get_payment_status(pid)
```
</details>

<details>
<summary>Фискализация 54-ФЗ (эквайринг)</summary>

```python
from tbank.acquiring.models import Receipt, ReceiptItem
from tbank.acquiring.enums import Tax, Taxation, PaymentObject

await client.init(InitRequest(
    amount=100000, order_id="A-1",
    receipt=Receipt(
        taxation=Taxation.USN_INCOME, email="client@example.com",
        items=[ReceiptItem(name="Товар", price=100000, quantity=1, amount=100000,
                           tax=Tax.VAT_22, payment_object=PaymentObject.COMMODITY)],
    ),
))
```
</details>

## ⚠️ Обработка ошибок

Все ошибки наследуются от `tbank.core.errors.TBankError`:

```python
from tbank.core.errors import TBankAPIError, TBankNetworkError, InsufficientFundsError

try:
    await client.charge(payment_id, rebill_id)
except InsufficientFundsError:
    ...                       # недостаточно средств (типизированное исключение)
except TBankAPIError as e:
    print(e.code, e.message)  # прочие ошибки API
except TBankNetworkError:
    ...                       # сеть/таймаут после ретраев
```

## 🔗 Ссылки

- 📚 Документация: https://tbank.readthedocs.io
- 🐙 Репозиторий: https://github.com/masasibata/tbank
- 🏦 API Т-Банка: https://developer.tbank.ru/docs/api

## 🧪 Разработка

```bash
poetry install
poetry run pytest --cov=tbank      # тесты + покрытие
poetry run mypy tbank              # строгая типизация
poetry run black tbank tests && poetry run isort tbank tests
```

## 📄 Лицензия

MIT — см. [LICENSE](LICENSE).
