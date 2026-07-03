# Партнёрская доставка (`tbank.delivery`)

Партнёрская доставка и выездные встречи: задания (создание, обновление, отмена),
подбор интервалов и назначение встречи, загрузка и скачивание документов.

- Хост: `business.tbank.ru/openapi` по **Bearer**-токену.
- Документы: загрузка — `multipart/form-data`, скачивание — «сырые» байты.
- Клиенты: `tbank.delivery.DeliveryClient` (async) и
  `tbank.delivery.sync.DeliveryClient` (sync).

## Задание и встреча

```python
from tbank.delivery import DeliveryClient
from tbank.delivery.models import (
    CreateTaskRequest, Contact, Phone, Passport,
    GetIntervalsRequest, Address, CreateMeetingRequest,
)
from tbank.delivery.enums import PhoneType

client = DeliveryClient(token="business-token")

# создать задание (Idempotency-Key генерируется автоматически)
task = await client.create_task(CreateTaskRequest(
    template="COURIER",
    contacts=[Contact(
        id="c-1", first_name="Иван",
        phones=[Phone(type=PhoneType.MOBILE, number="+79001112233")],
        documents=[Passport(number="123456", series="4509")],
    )],
))

# подобрать интервал и назначить встречу
intervals = await client.get_intervals(GetIntervalsRequest(
    address=Address(full_address="Москва, ул. Тверская, 1"), task_ids=[task.id],
))
slot = intervals.intervals[0]
await client.create_meeting(CreateMeetingRequest(
    appointment_id=intervals.appointment_id,
    interval_start_time=slot.start_interval,
    interval_end_time=slot.end_interval,
))

info = await client.get_task(task.id)      # статус, вложения, фото
```

## Документы

```python
# загрузить документ (multipart) и связать с заданием
uploaded = await client.upload_document(
    task_id=task.id, document_type="ACT", content=pdf_bytes, filename="act.pdf",
)

# скачать документ — вернутся байты
content = await client.download_document(uploaded.id)
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.delivery.aio.DeliveryClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.delivery.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.delivery.enums
   :members:
   :undoc-members:
```
