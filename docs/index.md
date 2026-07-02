# tbank

[![PyPI](https://img.shields.io/pypi/v/tbank.svg)](https://pypi.org/project/tbank/)
[![Python](https://img.shields.io/pypi/pyversions/tbank.svg)](https://pypi.org/project/tbank/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/masasibata/tbank/blob/main/LICENSE)

**Асинхронный и синхронный Python SDK для API Т-Банка (ex-Тинькофф).**

Один пакет — оба мира Т-Банка: интернет-эквайринг (приём платежей, СБП, рекуррент,
фискализация 54-ФЗ) и открытый банковский API Т-Бизнеса (счета, выписки, рублёвые
платежи, инвойсы, СБП-ссылки). Всё на общем типизированном ядре.

## Особенности

- 🚀 **Async и sync** — один API в двух вариантах на общем ядре (`httpx`).
- 🛡️ **Строгая типизация** — pydantic v2, `mypy --strict`, `py.typed`.
- 🔌 **Полное покрытие** — эквайринг (EACQ) и открытый банк (T-API) в одном пакете.
- 🔐 **Аутентификация из коробки** — SHA-256 Token-подпись, Bearer и **mTLS**.
- 💸 **Корректные деньги** — копейки (`int`) для эквайринга, `Decimal` для открытого банка.
- 🔁 **Надёжность** — ретраи с бэкоффом, идемпотентность.

## Установка

```bash
pip install tbank
```

## Быстрый пример

```python
from tbank.acquiring import AcquiringClient
from tbank.acquiring.models import InitRequest

async with AcquiringClient(terminal_key="...", password="...") as client:
    payment = await client.init(InitRequest(amount=150000, order_id="A-1"))
    print(payment.payment_url)   # редиректим покупателя
```

## Домены

| Пакет | Что покрыто |
| --- | --- |
| [`tbank.acquiring`](acquiring.md) | Приём платежей, вебхуки, рекуррент, карты, СБП QR, фискализация 54-ФЗ, привязка карт |
| [`tbank.business`](business.md) | Счета и балансы, выписки, рублёвые платежи через mTLS, инвойсы, СБП-ссылки b2b |

```{toctree}
:maxdepth: 2
:caption: Начало работы
:hidden:

installation
quickstart
authentication
errors
webhooks
```

```{toctree}
:maxdepth: 2
:caption: Домены
:hidden:

acquiring
business
```

```{toctree}
:maxdepth: 2
:caption: Справочник
:hidden:

core
changelog
```

## Ссылки

- 🐙 Репозиторий: <https://github.com/masasibata/tbank>
- 📦 PyPI: <https://pypi.org/project/tbank/>
- 🏦 API Т-Банка: <https://developer.tbank.ru/docs/api>
