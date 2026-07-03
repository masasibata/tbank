# Changelog

## 1.14.0

- Рефакторинг доменов: декларации `Endpoint` вынесены в модуль `_endpoints.py`
  каждого домена и переиспользуются sync/aio-клиентами.
- Ядро: адреса хостов централизованы в `tbank.core.urls`; транспорты собираются
  фабриками `build_sync_transports` / `build_async_transports`.
- Ядро: единый разбор T-API error-ответов — `error_from_tapi_response`
  в `tbank.core.errors`; доменные `errors.py` сведены к тонким обёрткам.
- Ядро (`client`): хелперы `dump_model`, `parse_as` (поддержка `TypeAdapter`
  для списков и oneOf), `page_params`, `ensure_idempotency_key`; флаг
  `decimal_body` для парсинга денежных сумм в `Decimal`; `_call` принимает
  словарь и валидирует его через `request_model` эндпоинта.
- Ретраи: неидемпотентные запросы (POST без `Idempotency-Key`) по умолчанию
  не повторяются (кроме 429), опция `RetryPolicy.retry_non_idempotent`;
  задержка учитывает `Retry-After` в секундах и в формате HTTP-даты.

## 1.13.0

- Новый домен **`tbank.mails`** — внутренние письма H2H: `push_incoming_mail`
  (mTLS + подпись), `mark_read`, `list_unread`.
- Новый домен **`tbank.files`** — файловое хранилище: `upload_file` и
  `download_file` (`application/octet-stream`, Bearer).
- Новый домен **`tbank.shopping`** — чаты магазина: `list_chats`, `get_chat`,
  `list_messages`, `send_message`, `upload_chat_file`, `download_chat_file` (mTLS).
- Ядро: HTTP-подпись вынесена в `tbank.core.signing.HttpSignature` и переиспользуется
  валютным контролем и письмами (`tbank.ved.CurrencySignature` — псевдоним).

## 1.12.0

- Новый домен **`tbank.ved`** — ВЭД / валютный контроль (4 метода):
  `register_contract`, `amend_contract`, `deregister_contract` и
  `get_application_status`.
  - Постановка/изменение/снятие идут на secured-хост (mTLS) и подписываются по
    схеме HTTP Signatures (HMAC-SHA256) через `CurrencySignature(key_id, secret)`;
    статус — по Bearer. Целочисленные перечисления контракта уходят числами.
  - Подпись реализована по стандарту draft-cavage — точная сборка строки подписи
    в спеке не приведена, требует сверки с реальным ключом.

## 1.11.0

- Новый домен **`tbank.deposit`** — депозиты (3 метода):
  `get_deposit_details` (баланс, ставка, условия, автопролонгация), `open_deposit`
  и `replenish_deposit`. На secured-хосте по mTLS; суммы — `Decimal` в валюте
  депозита.

## 1.10.0

- Новый домен **`tbank.tax_consult`** — налоговые консультации (13 методов):
  - Заявка и чат: `get_request`, `get_chat`, `send_message`.
  - Вложения: `upload_attachment` (`octet-stream`), `download_attachment` (байты).
  - Воркфлоу (оптимистичная блокировка через `If-Match`/`cas_version`):
    `start_review`, `start_work`, `request_clarification`, `decline`, `cancel`,
    `set_pending_payment`, `confirm_payment`, `mark_ready`.
  - Весь домен — на secured-хосте по mTLS.
- Ядро: транспорт теперь поддерживает и `content` (binary-тело) — для
  `application/octet-stream`-запросов.

## 1.9.0

- Новый домен **`tbank.delivery`** — партнёрская доставка (8 методов):
  - Задания: `create_task` (с `Idempotency-Key`), `get_task`, `update_task`,
    `cancel_task`.
  - Встречи: `get_intervals` (подбор интервалов по адресу), `create_meeting`.
  - Документы: `upload_document` (`multipart/form-data`) и `download_document`
    (сырые байты).
- Ядро: транспорт (`AsyncTransport`/`SyncTransport`) теперь поддерживает
  `data`/`files` для `multipart/form-data`-запросов.

## 1.8.0

- Новый домен **`tbank.business_cards`** — бизнес-карты (14 методов):
  - Карты: `list_cards`, `get_card`, `get_virtual_card_requisites`, `block_card`,
    `list_company_cards` (v3).
  - Выпуск виртуальных карт: `create_virtual_card_application`,
    `get_virtual_card_application`, `list_virtual_card_applications` (v3);
    перевыпуск — `reissue_virtual_card` + `get_reissue_result`.
  - Лимиты: `get_card_limits`, `set_cash_limit`, `set_spend_limit`,
    `set_batch_limits` (пакетно, до 10 000 карт).
  - Перевыпуск, расходный лимит, пакетные лимиты и методы `v3` — на secured-хосте
    по mTLS, остальное — по Bearer. Суммы — `Decimal` в рублях.

## 1.7.0

- Новый домен **`tbank.merchant_acquiring`** — торговый (POS) эквайринг:
  `list_terminals` (постранично) и `list_operations` (операции по терминалу за
  период). Обычный хост по Bearer; суммы — в копейках (`int`). Отдельный API от
  интернет-эквайринга `tbank.acquiring`.

## 1.6.0

- Новый домен **`tbank.overnight`** — овернайты (размещение остатка счёта на ночь):
  `get_overnight_info` (сумма, ставка, автоплатёж, текущая сделка, настройки) и
  `replenish_overnight`. На secured-хосте по mTLS; суммы T-API отдаёт строками.
- Новый домен **`tbank.special_accounts`** — специальные счета:
  `get_arrest_etp_operations` (аресты средств и картотеки ЭТП за период). На
  обычном хосте по Bearer; суммы — `Decimal` в рублях.

## 1.5.0

- Новый домен **`tbank.direct_debit`** — безакцептные списания (15 методов):
  - Соглашения: `list_agreements`, `get_agreement`, `get_agreement_file` (PDF),
    `get_agreement_url` (ссылка на подписание контрагентом).
  - Правила: `create_rule` (рекуррентное `RecurrentRuleCreate` по `cron` или
    триггерное `TriggerRuleCreate` по факту пополнения), `get_rule`/`update_rule`
    (карточка — дискриминированное объединение `Recurrent`/`Trigger`),
    `delete_rule`, `list_rules`, `list_rules_v2`.
  - Платёжные требования: `create_payment_request`, `list_payment_requests`,
    `get_payment_request`, `revoke_payment_request`, `get_payment_request_file`
    (PDF).
  - Весь домен — на secured-хосте по mTLS. Создание/отзыв — с `Idempotency-Key`.
    Суммы — `Decimal` в рублях.

## 1.4.0

- Новый домен **`tbank.nominal_accounts`** — номинальные счета (48 методов):
  - Бенефициары: `create_beneficiary`, `get_beneficiary`, `update_beneficiary`,
    `list_beneficiaries`; типы бенефициаров (ФЛ/ИП/ЮЛ, резидент/нерезидент, lite) —
    дискриминированное объединение по `type`.
  - Банковские реквизиты бенефициара (РКЦ/карта/СБП): `create_bank_details`,
    `get_bank_details`, `update_bank_details`, `delete_bank_details`,
    `set_default_bank_details`, `list_bank_details`; запросы на добавление карты
    (`create_add_card_request`, `get_add_card_request`) и скоринг
    (`get_beneficiaries_scoring`).
  - Сделки и этапы: `create_deal`/`get_deal`/`delete_deal`/`accept_deal`/`cancel_deal`/
    `draft_deal`/`get_deal_validity`/`list_deals`; `create_step`/`get_step`/
    `update_step`/`delete_step`/`complete_step`/`list_steps`; депоненты и реципиенты
    этапа с обновлением реквизитов реципиента.
  - Платежи (обычные и налоговые), балансы, холды, неидентифицированные пополнения
    (`identify_incoming_transaction`) и переводы между виртуальными счетами.
  - Просмотр карточек сделки/этапа/платежа, проверка сделки и переводы — на
    secured-хосте по mTLS, остальное — по Bearer. Создание ресурсов — с
    `Idempotency-Key`. Суммы — `Decimal` в рублях.

## 1.3.0

- Новый домен **`tbank.salary`** — зарплатный проект:
  - Сотрудники: `add_employees_by_requisites`, `create_employees` (черновики анкет),
    `list_employees` + опрос результатов.
  - Платёжные реестры: `create_payment_registry`, `create_and_submit_registry`
    (создать и подписать одним вызовом), `submit_payment_registry`, `pay_payment_registry`,
    `cancel_payment_registry` + опрос результатов; `list_payment_registries`,
    `get_payment_registry`.
  - Async-модель через клиентский `correlationId` (оплата — ключ идемпотентности `id`).
    Подписание/оплата/отмена/список реестров — на secured-хосте по mTLS, анкеты и
    создание черновика — на обычном хосте по Bearer. Суммы — `Decimal` в рублях.

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
