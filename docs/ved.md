# ВЭД — валютный контроль (`tbank.ved`)

Постановка валютного контракта на учёт, внесение изменений, снятие с учёта и
проверка статуса заявления.

- Хосты: постановка/изменение/снятие — на `secured-openapi.tbank.ru` (**mTLS**,
  `cert`) и требуют **криптоподписи** запроса; статус заявления — на
  `business.tbank.ru/openapi` по **Bearer**.
- Подпись: схема **HTTP Signatures (HMAC-SHA256)**. `keyId` и секрет выдаёт
  менеджер Т-Банка. Передаётся в клиент как
  `signature=CurrencySignature(key_id, secret)`.
- Суммы: **`Decimal`**. Провод: `camelCase`; целочисленные перечисления
  (`ContractSubject`, `ContractType` и др.) уходят числами.
- Клиенты: `tbank.ved.VedClient` (async) и `tbank.ved.sync.VedClient` (sync).

```{warning}
Точная сборка строки подписи в OpenAPI-спеке приведена не полностью (без примера).
`CurrencySignature` реализует стандарт **draft-cavage**: строка подписи — это
построчное объединение подписываемых заголовков (`(request-target)`, `date`,
`data`). Перед боевым использованием сверьте подпись с реальным ключом.
```

```python
from decimal import Decimal
from tbank.ved import VedClient, CurrencySignature
from tbank.ved.models import RegisterContractRequest, ContractInfo, Counterparty
from tbank.ved.enums import ContractSubject, ContractType

client = VedClient(
    token="business-token",
    cert=("client.pem", "client-key.pem"),           # mTLS
    signature=CurrencySignature("key-id", "secret"),  # выдаёт менеджер
)

# поставить контракт на учёт
res = await client.register_contract(RegisterContractRequest(
    open_api_application_id="APP-1",
    contract_info=ContractInfo(
        contract_subject=ContractSubject.GOODS,
        contract_type=ContractType.EXPORT,
        currency_code="840",
        contract_date="2026-01-10",
        exchange_rate_effective_date="2026-01-10",
        amount=Decimal("100000"),
        counterparty=[Counterparty(name="ACME Inc", country_code="840")],
    ),
))

# проверить статус заявления (Bearer, без подписи)
status = await client.get_application_status(res.open_api_application_id)
print(status.status, status.metadata.unique_contract_number)
```

Изменение и снятие с учёта — `amend_contract` и `deregister_contract`.

## Клиент

```{eval-rst}
.. autoclass:: tbank.ved.aio.VedClient
   :members:
```

## Подпись

```{eval-rst}
.. autoclass:: tbank.ved.signing.CurrencySignature
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.ved.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.ved.enums
   :members:
   :undoc-members:
```
