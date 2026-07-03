# Номинальные счета (`tbank.nominal_accounts`)

Номинальный счёт — счёт, на котором компания-оператор держит деньги в интересах
третьих лиц (бенефициаров). SDK покрывает весь жизненный цикл: бенефициары и их
банковские реквизиты, скоринг в финмониторинге, сделки с этапами и
депонентами/реципиентами, платежи (обычные и налоговые), балансы, холды и
переводы между виртуальными счетами.

- Хосты: большинство методов — на `business.tbank.ru/openapi` по **Bearer**-токену;
  просмотр карточек сделки, этапа и платежа, проверка сделки и все операции с
  переводами — на `secured-openapi.tbank.ru` по **mTLS** (`cert`).
- Идемпотентность: методы создания ресурсов принимают `idempotency_key`
  (по умолчанию генерируется автоматически) — уходит в заголовок `Idempotency-Key`.
- Суммы: **`Decimal` в рублях**. Провод: `camelCase`.
- Клиенты: `tbank.nominal_accounts.NominalAccountsClient` (async) и
  `tbank.nominal_accounts.sync.NominalAccountsClient` (sync).

## Полиморфные модели

Бенефициары, банковские реквизиты, платежи, скоринг и запросы на добавление карты —
дискриминированные объединения. Тип выбирается по полю `type` (или `status`), SDK
сам разбирает ответ в конкретный класс:

```python
from tbank.nominal_accounts.models import (
    BeneficiaryFlResidentResponse, CardBankDetailsResponse, RegularPaymentResponse,
)

b = await client.get_beneficiary("b-1")
if isinstance(b, BeneficiaryFlResidentResponse):
    print(b.snils)
```

## Бенефициары и реквизиты

```python
from tbank.nominal_accounts import NominalAccountsClient
from tbank.nominal_accounts.models import (
    BeneficiaryFlResidentRequest, Address, Passport, RkcBankDetailsRequest,
)

client = NominalAccountsClient(token="business-token")

# создать бенефициара (физлицо-резидент)
b = await client.create_beneficiary(BeneficiaryFlResidentRequest(
    first_name="Иван", last_name="Петров", is_self_employed=True,
    birth_date="1990-05-01", citizenship="RU",
    documents=[Passport(serial="4509", number="123456",
                        issued_on="2010-06-01", division="770-001")],
    addresses=[Address(type="REGISTRATION_ADDRESS", address="Москва")],
))

# добавить реквизиты для выплат (по банковским реквизитам)
bd = await client.create_bank_details(b.beneficiary_id, RkcBankDetailsRequest(
    bik="044525225", bank_name="Т-Банк",
    account_number="40817810000000000001",
    corr_account_number="30101810000000000225",
))
await client.set_default_bank_details(b.beneficiary_id, bd.bank_details_id)

# проверка в финмониторинге
await client.get_beneficiaries_scoring(beneficiary_id=b.beneficiary_id, passed=True)
```

## Сделка, этапы, реципиенты

```python
from tbank.nominal_accounts.models import (
    DealRequest, StepRequest, RecipientRequest, DeponentRequest,
)
from decimal import Decimal

deal = await client.create_deal(DealRequest(account_number="40817810000000000001"))
step = await client.create_step(deal.deal_id, StepRequest(description="Этап 1"))

# кто вносит деньги (депонент) и кто получает (реципиент)
await client.set_deponent(deal.deal_id, step.step_id, payer_id,
                          DeponentRequest(amount=Decimal("10000")))
await client.create_recipient(deal.deal_id, step.step_id, RecipientRequest(
    beneficiary_id=b.beneficiary_id, amount=Decimal("10000"), purpose="Оплата услуг",
))

await client.accept_deal(deal.deal_id)                 # согласовать сделку
await client.get_deal_validity(deal.deal_id)           # mTLS: можно ли платить
await client.complete_step(deal.deal_id, step.step_id) # провести выплаты
```

## Платежи и виртуальные счета

```python
from tbank.nominal_accounts.models import (
    CreateRegularPaymentRequest, CreateTransferRequest, TransferParty,
)

# обычный платёж бенефициару
pay = await client.create_payment(CreateRegularPaymentRequest(
    beneficiary_id=b.beneficiary_id, account_number="40817810000000000001",
    amount=Decimal("500.00"), purpose="Выплата",
))
await client.get_payment(pay.payment_id)               # mTLS

# балансы и холды на виртуальных счетах
await client.list_balances(account_number="40817810000000000001")
await client.list_holds(beneficiary_id=b.beneficiary_id)

# перевод между виртуальными счетами (mTLS)
await client.create_transfer(CreateTransferRequest(
    account_number="40817810000000000001",
    from_=TransferParty(beneficiary_id=payer_id),
    to=TransferParty(beneficiary_id=b.beneficiary_id),
    amount=Decimal("300"),
))
```

Неопознанные входящие пополнения разбираются через `list_incoming_transactions`
и `identify_incoming_transaction` (распределение суммы по бенефициарам).

## Клиент

```{eval-rst}
.. autoclass:: tbank.nominal_accounts.aio.NominalAccountsClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.nominal_accounts.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.nominal_accounts.enums
   :members:
   :undoc-members:
```
