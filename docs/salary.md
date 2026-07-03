# Зарплатный проект (`tbank.salary`)

Зарплатные выплаты сотрудникам: регистрация анкет, платёжные реестры, их
создание, подписание (в т.ч. «создать и подписать» одним вызовом), оплата и
отмена. Операции **асинхронные**: инициатор возвращает клиентский `correlationId`
(оплата — ключ идемпотентности `id`), по которому опрашивается результат.

- Хосты: анкеты, создание черновика реестра и карточка — на
  `business.tbank.ru/openapi` по **Bearer**-токену; подписание, создание-и-подписание,
  оплата, отмена и список реестров — на `secured-openapi.tbank.ru` по **mTLS**
  (`cert`).
- Суммы: **`Decimal` в рублях**. Провод: `camelCase`.
- Клиенты: `tbank.salary.SalaryClient` (async) и `tbank.salary.sync.SalaryClient` (sync).

## Сценарий выплаты зарплаты

```python
from decimal import Decimal
from tbank.salary import SalaryClient
from tbank.salary.models import (
    CreateSubmitRegistryRequest, RegistryPayment, RegistryEmployeeInfo, PayRegistryRequest,
)

client = SalaryClient(
    token="self-service-token",
    cert=("client.pem", "client-key.pem"),   # mTLS для подписания/оплаты
)

# создать и сразу подписать реестр (mTLS) → correlationId
cid = await client.create_and_submit_registry(CreateSubmitRegistryRequest(
    payments=[RegistryPayment(
        number=1, account_number="40817810000000000001",
        payment_purpose="Зарплата за июнь",
        employee_info=RegistryEmployeeInfo(first_name="Иван", last_name="Петров"),
        sum=Decimal("50000.75"),
        period_start="2026-06-01", period_end="2026-06-30",
    )],
))
res = await client.get_create_submit_result(cid)     # → paymentRegistryId, ACCEPTED

# оплатить (mTLS) → возвращает ключ идемпотентности id
await client.pay_payment_registry(PayRegistryRequest(
    payment_registry_id=res.payment_registry_id,
    account_number="40702810000000000000", purpose="Зарплата за июнь",
))
```

Раздельный поток тоже доступен: `create_payment_registry` → `submit_payment_registry`
→ `pay_payment_registry`; отменить отправку — `cancel_payment_registry`.

## Сотрудники

```python
from tbank.salary.models import (
    AddEmployeesByRequisitesRequest, EmployeeByRequisites, EmployeeBankInfo,
    CreateEmployeesRequest, EmployeeDraft, JobInfo, ListEmployeesRequest,
)

# добавить по реквизитам → correlationId, затем опросить результат
cid = await client.add_employees_by_requisites(AddEmployeesByRequisitesRequest(
    employees=[EmployeeByRequisites(
        number=1, first_name="Иван", last_name="Петров",
        bank_info=EmployeeBankInfo(account_number="40817810000000000001"),
    )],
))
await client.get_add_employees_result(cid)

# полная анкета (черновик)
await client.create_employees(CreateEmployeesRequest(employees=[EmployeeDraft(
    number=1, first_name="Иван", last_name="Петров",
    birth_date="1990-01-02", birth_place="Москва", citizenship="РФ",
    job_info=JobInfo(position="Инженер"),
)]))

# информация по сотрудникам
await client.list_employees(ListEmployeesRequest(employee_ids=[7, 8]))
```

## Реестры

```python
from tbank.salary.models import ListRegistriesRequest
from tbank.salary.enums import RegistryStatus

await client.list_payment_registries(ListRegistriesRequest(
    statuses=[RegistryStatus.EXECUTED], period_start="2026-01-01", period_end="2026-06-30",
))
info = await client.get_payment_registry(registry_id)   # суммы, статусы, платежи
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.salary.aio.SalaryClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.salary.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.salary.enums
   :members:
   :undoc-members:
```
