# Установка

```bash
pip install tbank
```

Или через poetry:

```bash
poetry add tbank
```

## Требования

- **Python 3.9+**
- [`pydantic`](https://docs.pydantic.dev/latest/) `>= 2.0`
- [`httpx`](https://www.python-httpx.org/) `>= 0.27`

Пакет типизирован (`py.typed`) — mypy и IDE видят все типы из коробки.

## Что дальше

- [Быстрый старт](quickstart.md) — первые запросы по обоим доменам.
- [Аутентификация](authentication.md) — Token-подпись, Bearer, mTLS.
