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
| [`tbank.dolyame`](dolyame.md) | Оплата частями (BNPL): жизненный цикл заказа, возвраты, доставка |
| [`tbank.tid`](tid.md) | T-ID: вход через Т-Банк (OAuth 2.0/OIDC), учётные данные, документы, статусы, компания, делегированная идентификация |
| [`tbank.selfemployed`](selfemployed.md) | Выплаты самозанятым (e2c): анкеты, платёжные реестры, подписание, оплата, чеки |
| [`tbank.salary`](salary.md) | Зарплатный проект: анкеты сотрудников, платёжные реестры, создание/подписание/оплата/отмена |
| [`tbank.nominal_accounts`](nominal_accounts.md) | Номинальные счета: бенефициары и реквизиты, скоринг, сделки/этапы/депоненты/реципиенты, платежи, балансы, холды, переводы |
| [`tbank.direct_debit`](direct_debit.md) | Безакцептные списания: соглашения, правила (рекуррентные и триггерные), платёжные требования |
| [`tbank.overnight`](overnight.md) | Овернайты: сводка по счёту, пополнение |
| [`tbank.special_accounts`](special_accounts.md) | Специальные счета: аресты средств и картотеки ЭТП |
| [`tbank.merchant_acquiring`](merchant_acquiring.md) | Торговый (POS) эквайринг: терминалы и операции по ним |
| [`tbank.business_cards`](business_cards.md) | Бизнес-карты: выпуск/перевыпуск виртуальных карт, реквизиты, лимиты, блокировка |
| [`tbank.delivery`](delivery.md) | Партнёрская доставка: задания, встречи и интервалы, документы (загрузка/скачивание) |
| [`tbank.tax_consult`](tax_consult.md) | Налоговые консультации: заявки, чат, вложения, переходы воркфлоу |
| [`tbank.deposit`](deposit.md) | Депозиты: карточка счёта, открытие и пополнение |
| [`tbank.ved`](ved.md) | ВЭД (валютный контроль): постановка/изменение/снятие контракта, статус (HTTP-подпись) |
| [`tbank.mails`](mails.md) | Письма (H2H): входящие письма, отметка о прочтении, непрочитанные |
| [`tbank.files`](files.md) | Файловое хранилище: загрузка и скачивание файлов |
| [`tbank.shopping`](shopping.md) | Шопинг — чаты магазина: чаты, сообщения, файлы |

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
dolyame
tid
selfemployed
salary
nominal_accounts
direct_debit
overnight
special_accounts
merchant_acquiring
business_cards
delivery
tax_consult
deposit
ved
mails
files
shopping
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
