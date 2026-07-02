# Выплаты самозанятым (`tbank.selfemployed`)

E2C-выплаты самозанятым: регистрация анкет, платёжные реестры, их подписание,
оплата и получение чеков. Все операции — **асинхронные**: инициирующий метод
возвращает клиентский `correlationId`, по которому затем опрашивается результат
`*_result`.

- Хосты: обычные операции (анкеты, создание реестра, карточка) — на
  `business.tbank.ru/openapi` по **Bearer**-токену; подписание, оплата, чеки и
  список реестров — на `secured-openapi.tbank.ru` и требуют **mTLS-сертификата**
  (`cert`).
- Суммы: **`Decimal` в рублях** (на проводе — number).
- Провод: `camelCase`.
- Клиенты: `tbank.selfemployed.SelfEmployedClient` (async) и
  `tbank.selfemployed.sync.SelfEmployedClient` (sync).

## Сценарий выплаты

```python
from decimal import Decimal
from tbank.selfemployed import SelfEmployedClient
from tbank.selfemployed.models import (
    AddRecipientsByRequisitesRequest, RecipientByRequisites, RecipientBankInfo,
    CreatePaymentRegistryRequest, RegistryPayment, SelfEmployedInfo,
)

client = SelfEmployedClient(
    token="self-service-token",
    cert=("client.pem", "client-key.pem"),   # mTLS для подписания/оплаты/чеков
)

# 1) добавить самозанятого по реквизитам → correlationId для опроса
cid = await client.add_recipients_by_requisites(AddRecipientsByRequisitesRequest(
    recipients=[RecipientByRequisites(
        number=1, first_name="Иван", last_name="Петров",
        inn="770012345678",
        bank_info=RecipientBankInfo(account_number="40817810000000000001"),
    )],
))
result = await client.get_add_recipients_result(cid)   # ждём CREATED

# 2) создать черновик платёжного реестра
cid = await client.create_payment_registry(CreatePaymentRegistryRequest(
    payments=[RegistryPayment(
        number=1, account_number="40817810000000000001",
        payment_purpose="Оплата услуг",
        self_employed_info=SelfEmployedInfo(first_name="Иван", last_name="Петров"),
        sum=Decimal("1500.50"),
    )],
))
created = await client.get_create_registry_result(cid)   # → paymentRegistryId
registry_id = created.payment_registry_id

# 3) подписать → 4) оплатить (mTLS)
await client.submit_payment_registry(registry_id)
sub = await client.get_submit_result(cid)                # ждём ACCEPTED
await client.pay_payment_registry(registry_id)
pay = await client.get_pay_result(cid)                   # статусы платежей

# 5) чеки самозанятых
await client.request_receipts(registry_id)
receipts = await client.get_receipts_result(cid)         # ссылки на чеки
```

`correlationId` генерируется SDK автоматически (можно передать свой через
`correlation_id=`). Инициирующие методы возвращают именно его.

## Самозанятые (анкеты)

```python
from tbank.selfemployed.models import (
    CreateRecipientsRequest, RecipientDraft, ListRecipientsRequest,
)
from tbank.selfemployed.enums import DocumentType, PhoneType

# полная анкета (черновик)
await client.create_recipients(CreateRecipientsRequest(recipients=[RecipientDraft(
    number=1, first_name="Иван", last_name="Петров",
    birth_date="1990-01-02", birth_place="Москва", citizenship="РФ",
)]))

# информация по самозанятым (фильтры + пагинация)
await client.list_recipients(ListRecipientsRequest(inn=["770012345678"], limit=50))
```

## Реестры

```python
from tbank.selfemployed.models import ListRegistriesRequest
from tbank.selfemployed.enums import RegistryStatus

# список реестров за период (mTLS)
await client.list_payment_registries(ListRegistriesRequest(
    statuses=[RegistryStatus.EXECUTED], period_start="2026-01-01", period_end="2026-06-30",
))
# карточка реестра
info = await client.get_payment_registry(registry_id)    # суммы, статусы, платежи
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.selfemployed.aio.SelfEmployedClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.selfemployed.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.selfemployed.enums
   :members:
   :undoc-members:
```
