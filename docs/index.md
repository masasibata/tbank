# tbank

Асинхронный и синхронный Python SDK для API Т-Банка (ex-Тинькофф): интернет-эквайринг
и открытый банковский API Т-Бизнеса в одном пакете, с общим ядром.

- 🚀 Async и sync на общем ядре (`httpx`)
- 🛡️ Строгая типизация (pydantic v2, `mypy --strict`)
- 🔐 SHA-256 Token-подпись, Bearer и mTLS из коробки
- 💸 Копейки (`int`) для эквайринга, `Decimal` для открытого банка
- 🔁 Ретраи с бэкоффом, идемпотентность

## Установка

```bash
pip install tbank
```

```{toctree}
:maxdepth: 2
:caption: Содержание

quickstart
reference
```

## Ссылки

- Репозиторий: <https://github.com/masasibata/tbank>
- API Т-Банка: <https://developer.tbank.ru/docs/api>
