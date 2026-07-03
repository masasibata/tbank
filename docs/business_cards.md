# Бизнес-карты (`tbank.business_cards`)

Управление корпоративными картами: выпуск и перевыпуск виртуальных карт,
реквизиты, блокировка, лимиты (расходный и на снятие наличных, в том числе
пакетно) и списки карт компании.

- Хосты: большинство методов — на `business.tbank.ru/openapi` по **Bearer**-токену;
  перевыпуск, общий расходный лимит, пакетная установка лимитов и методы `v3`
  (списки заявок и карт компании) — на `secured-openapi.tbank.ru` по **mTLS** (`cert`).
- Суммы: **`Decimal` в рублях** (пакетные лимиты `v3` — целые). Провод: `camelCase`.
- Клиенты: `tbank.business_cards.BusinessCardsClient` (async) и
  `tbank.business_cards.sync.BusinessCardsClient` (sync).

## Выпуск виртуальной карты

```python
from tbank.business_cards import BusinessCardsClient
from tbank.business_cards.models import CreateApplicationRequest
from tbank.business_cards.enums import CardNetwork

client = BusinessCardsClient(
    token="business-token",
    cert=("client.pem", "client-key.pem"),   # mTLS нужен для v3 и лимитов
)

app = await client.create_virtual_card_application(CreateApplicationRequest(
    employee_identification_application_id="emp-app-1",
    account_number="40802810000000000001",
    card_network=CardNetwork.MIR,
))
status = await client.get_virtual_card_application(app.card_issue_application_id)
if status.ucid:
    requisites = await client.get_virtual_card_requisites(status.ucid)
    print(requisites.number, requisites.cvc, requisites.expiry_date.month)
```

## Лимиты и блокировка

```python
from decimal import Decimal
from tbank.business_cards.models import (
    SetLimitRequest, BlockCardRequest, SetBatchLimitsRequest, BatchLimitItem, BatchLimitValue,
)
from tbank.business_cards.enums import InputLimitPeriod, CardBlockReason

# лимит на снятие наличных (Bearer) и общий расходный лимит (mTLS)
await client.set_cash_limit(ucid, SetLimitRequest(
    limit_value=Decimal("50000"), limit_period=InputLimitPeriod.MONTH,
))
await client.set_spend_limit(ucid, SetLimitRequest(
    limit_value=Decimal("200000"), limit_period=InputLimitPeriod.MONTH,
))
limits = await client.get_card_limits(ucid)
print(limits.spend_limit.limit_remain)

# пакетная установка лимитов (mTLS, до 10 000 карт)
await client.set_batch_limits(SetBatchLimitsRequest(limits=[
    BatchLimitItem(ucid=ucid, spend_limit=BatchLimitValue(
        limit_period=InputLimitPeriod.DAY, limit_value=100000)),
]))

# блокировка
await client.block_card(ucid, BlockCardRequest(reason=CardBlockReason.LOST))
```

## Перевыпуск и списки

```python
app = await client.reissue_virtual_card(ucid)         # mTLS → correlationId
result = await client.get_reissue_result(app.correlation_id)
if result.status.value == "READY":
    print(result.info.new_ucid)

await client.list_cards(account_number="40802810000000000001")
await client.list_company_cards()                     # v3, mTLS
await client.list_virtual_card_applications(limit=50, offset=0)   # v3, mTLS
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.business_cards.aio.BusinessCardsClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.business_cards.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.business_cards.enums
   :members:
   :undoc-members:
```
