# Специальные счета (`tbank.special_accounts`)

Специальные счета участников закупок: аресты средств и картотеки ЭТП
(электронных торговых площадок). SDK покрывает выгрузку операций за период.

- Хост: `business.tbank.ru/openapi` по **Bearer**-токену.
- Суммы: **`Decimal` в рублях**. Провод: `camelCase`.
- Клиенты: `tbank.special_accounts.SpecialAccountsClient` (async) и
  `tbank.special_accounts.sync.SpecialAccountsClient` (sync).

```python
from tbank.special_accounts import SpecialAccountsClient

client = SpecialAccountsClient(token="business-token")

ops = await client.get_arrest_etp_operations(
    account_number="40817810000000000001",
    from_date="2026-01-01",
    till="2026-06-30",
)
print(ops.arrests.sum)                 # общая сумма арестов
for arrest in ops.arrests.values or []:
    print(arrest.amount, arrest.unblock_date)
for fee in ops.etp_fees or []:
    print(fee.amount, fee.recipient.name)
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.special_accounts.aio.SpecialAccountsClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.special_accounts.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.special_accounts.enums
   :members:
   :undoc-members:
```
