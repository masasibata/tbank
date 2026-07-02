# Changelog

## 0.1.0

Первый релиз.

**Эквайринг (`tbank.acquiring`, EACQ):**

- Приём платежей: `init`, `get_state`, `confirm`, `cancel`.
- Вебхуки: разбор и проверка подписи (`parse_notification`, `verify_notification`).
- Рекуррент: `charge` (по `RebillId`), поле `recurrent` в `init`.
- Клиенты и карты: `add_customer`, `get_customer`, `remove_customer`,
  `get_card_list`, `remove_card`.
- СБП QR: `get_qr`, `get_qr_members`; СБП-рекуррент: `add_account_qr`,
  `get_add_account_qr_state`, `charge_qr`.
- Фискализация 54-ФЗ: объект `Receipt` в `init`/`charge`/`charge_qr`,
  `send_closing_receipt`.
- Привязка карт: `add_card`, `get_add_card_state`; статус возврата СБП `get_qr_state`.

**Открытый банк (`tbank.business`, T-API):**

- Счета и выписки: `get_accounts`, `get_statement`, `iter_statement`
  (курсорная авто-пагинация), `get_bank_statement`.
- Рублёвые платежи через mTLS: `create_ruble_payment` (с налоговым блоком),
  `get_payment_status`, `get_documents_status`.
- Инвойсы: `send_invoice`, `get_invoice_info`.
- СБП-ссылки b2b: `create_onetime_qr`, `create_reusable_qr`, `get_qr_info`.

**Ядро:**

- Async и sync транспорт на `httpx`, ретраи с бэкоффом.
- Аутентификация: SHA-256 Token-подпись, Bearer, mTLS.
- Строгая типизация (pydantic v2, `mypy --strict`), `py.typed`.
