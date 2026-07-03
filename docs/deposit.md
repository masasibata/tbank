# Депозиты (`tbank.deposit`)

Депозитные счета компании: карточка депозита (баланс, ставка, условия,
автопролонгация), открытие нового депозита и пополнение.

- Хост: `secured-openapi.tbank.ru`, требуется **mTLS-сертификат** (`cert`).
- Суммы: **`Decimal`** в валюте депозита. Провод: `camelCase`.
- Клиенты: `tbank.deposit.DepositClient` (async) и
  `tbank.deposit.sync.DepositClient` (sync).

```python
from decimal import Decimal
from tbank.deposit import DepositClient
from tbank.deposit.models import OpenDepositRequest, ReplenishDepositRequest
from tbank.deposit.enums import Capitalisation, Currency, PayFrequency

client = DepositClient(
    token="business-token",
    cert=("client.pem", "client-key.pem"),
)

# карточка депозита
details = await client.get_deposit_details("D-АГ-123")
print(details.balance.amount, details.account_info.rate)
print(details.account_info.replenish.is_accessible)

# открыть депозит
opened = await client.open_deposit(OpenDepositRequest(
    term=181,
    capitalisation=Capitalisation.DEPOSIT,
    currency=Currency.RUB,
    is_replenish_available=True,
    is_withdraw_available=False,
    pay_frequency=PayFrequency.MATURITY,
))
print(opened.open_id, opened.application_id)

# пополнить депозит с расчётного счёта
await client.replenish_deposit(ReplenishDepositRequest(
    deposit_agreement="D-АГ-123",
    source_agreement="40702810000000000000",
    amount=Decimal("50000"),
))
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.deposit.aio.DepositClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.deposit.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.deposit.enums
   :members:
   :undoc-members:
```
