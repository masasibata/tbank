# Безакцептные списания (`tbank.direct_debit`)

Списание средств со счёта плательщика по заранее подписанному соглашению — без
подтверждения каждой операции. SDK покрывает три сущности: **соглашения** (основа
для списаний), **правила** (рекуррентные — по расписанию `cron`, и триггерные — по
факту пополнения) и **платёжные требования** (разовые списания/пополнения).

- Хост: весь домен работает на `secured-openapi.tbank.ru` и требует
  **mTLS-сертификата** (`cert`).
- Идемпотентность: создание правил/требований и отзыв требования принимают
  `idempotency_key` (по умолчанию генерируется автоматически).
- Суммы: **`Decimal` в рублях**. Провод: `camelCase`.
- Клиенты: `tbank.direct_debit.DirectDebitClient` (async) и
  `tbank.direct_debit.sync.DirectDebitClient` (sync).

## Соглашения

```python
from tbank.direct_debit import DirectDebitClient

client = DirectDebitClient(
    token="business-token",
    cert=("client.pem", "client-key.pem"),   # mTLS обязателен
)

# ссылка на подписание соглашения контрагентом
url = await client.get_agreement_url()

# список и карточка соглашений
agreements = await client.list_agreements()
agreement = await client.get_agreement(agreements.results[0].id)
pdf = await client.get_agreement_file(agreement.id)   # content — base64 PDF
```

## Правила

```python
from decimal import Decimal
from tbank.direct_debit.models import (
    RecurrentRuleCreate, TriggerRuleCreate, PaymentRequisites,
    TriggerAmount, ReplenishmentFilter,
)

requisites = PaymentRequisites(
    payer_account="40817810000000000001", payer_name="ООО Ромашка",
    payer_inn="1234567890", payer_kpp="0", payer_bic="044525225",
    payer_cor_account="30101810000000000225",
    recipient_account="40702810000000000000", purpose="Абонентская плата",
    amount=Decimal("1500.00"),
)

# рекуррентное правило — списание по расписанию
await client.create_rule(RecurrentRuleCreate(
    agreement_id=agreement.id, cron_expr="0 12 1 * *", requisites=requisites,
))

# триггерное правило — списание процента от каждого пополнения
await client.create_rule(TriggerRuleCreate(
    agreement_id=agreement.id,
    amount=TriggerAmount(percent=Decimal("0.1")),      # 10%
    replenishment_filter=ReplenishmentFilter(category="MerchantAcq"),
    requisites=requisites,
))

# список (v2 — с полной карточкой), обновление, удаление
rules = await client.list_rules_v2(agreement_id=agreement.id)
rule = await client.get_rule(rules.results[0].id)
await client.delete_rule(rule.id)
```

`get_rule`/`update_rule` возвращают `RecurrentRuleDetails` либо
`TriggerRuleDetails` — SDK разбирает ответ по полю `type`.

## Платёжные требования

```python
from tbank.direct_debit.models import CreatePaymentRequest

req = await client.create_payment_request(CreatePaymentRequest(
    payer_account="40817810000000000001", payer_name="ООО Ромашка",
    payer_inn="1234567890", payer_kpp="0", payer_bic="044525225",
    payer_cor_account="30101810000000000225",
    recipient_account="40702810000000000000", purpose="Оплата по счёту №5",
    amount=Decimal("10000.00"),
))

await client.list_payment_requests(start_date="2026-01-01", end_date="2026-06-30")
details = await client.get_payment_request(req.id)
pdf = await client.get_payment_request_file(req.id)    # content — base64 PDF
await client.revoke_payment_request(req.id)            # отозвать
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.direct_debit.aio.DirectDebitClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.direct_debit.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.direct_debit.enums
   :members:
   :undoc-members:
```
