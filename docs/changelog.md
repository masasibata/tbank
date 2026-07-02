# Changelog

## 1.2.0

- Новый домен **`tbank.selfemployed`** — выплаты самозанятым (e2c):
  - Самозанятые: `create_recipients` (черновики анкет), `add_recipients_by_requisites`,
    `list_recipients` + опрос результатов `get_*_result`.
  - Платёжные реестры: `create_payment_registry`, подписание `submit_payment_registry`,
    оплата `pay_payment_registry`, чеки `request_receipts` + опрос результатов;
    `list_payment_registries`, `get_payment_registry`.
  - Async-модель submit→pay→result через клиентский `correlationId` (генерируется
    автоматически). Подписание/оплата/чеки/список реестров — на secured-хосте по mTLS,
    анкеты и создание реестра — на обычном хосте по Bearer. Суммы — `Decimal` в рублях.

## 1.1.0

- Новый домен **`tbank.tid`** — T-ID:
  - Вход через Т-Банк по OAuth 2.0 / OIDC (`TidOAuth`): `build_authorization_url`
    (в т.ч. PKCE), `fetch_token`, `refresh_token`, `fetch_client_credentials_token`,
    `introspect`, `revoke`, `get_userinfo` на `id.tbank.ru`.
  - Data-эндпоинты (`TidClient`): учётные данные, ИНН/СНИЛС, паспорт, водительские
    удостоверения, адреса, дебетовые счета; статусы идентификации, самозанятости,
    иностранного агента, ПДЛ и чёрных списков; информация о компании (T-Business ID)
    и делегированная идентификация.
- Эквайринг: альтернативная оплата и служебные методы — `get_tinkoff_pay_status`,
  `get_tinkoff_pay_link`, `get_tinkoff_pay_qr`, `get_sber_pay_link`, `get_sber_pay_qr`,
  `get_mir_pay_deeplink`, `check_order`, `resend`.

## 1.0.0

Стабильный релиз.

- Новый домен **`tbank.dolyame`** — оплата частями (BNPL): жизненный цикл заказа
  (`create_order`, `get_order`, `commit`, `cancel`, `refund`, `correction`,
  `complete_delivery`), вебхуки, аутентификация mTLS + HTTP Basic.
- Полная документация (Sphinx + readthedocs): гайды по аутентификации, ошибкам и
  вебхукам, справочник всех методов и моделей (autodoc-pydantic).

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
