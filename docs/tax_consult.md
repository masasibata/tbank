# Налоговые консультации (`tbank.tax_consult`)

Обработка заявок на налоговые консультации со стороны партнёра-исполнителя:
карточка заявки, чат с клиентом, вложения и переходы воркфлоу (взять в работу,
запросить уточнение, выставить оплату, отметить готовой и т.д.).

- Хост: `secured-openapi.tbank.ru`, требуется **mTLS-сертификат** (`cert`).
- Воркфлоу использует оптимистичную блокировку: передавайте `cas_version` из
  карточки заявки — он уходит в заголовок `If-Match` и защищает от гонок.
- Вложения: загрузка — `octet-stream` + заголовки имени/типа файла, скачивание —
  «сырые» байты.
- Клиенты: `tbank.tax_consult.TaxConsultClient` (async) и
  `tbank.tax_consult.sync.TaxConsultClient` (sync).

## Заявка, чат и воркфлоу

```python
from tbank.tax_consult import TaxConsultClient
from tbank.tax_consult.models import SendMessageRequest

client = TaxConsultClient(
    token="business-token",
    cert=("client.pem", "client-key.pem"),
)

req = await client.get_request(tax_request_id)     # статус, версия, флаг непрочитанных
print(req.status, req.cas_version)

# взять в работу и переписываться с клиентом
state = await client.start_review(tax_request_id, req.cas_version)
state = await client.start_work(tax_request_id, state.cas_version)

chat = await client.get_chat(tax_request_id, limit=50, offset=0)
await client.send_message(tax_request_id, SendMessageRequest(text="Уточните ИНН"))

# выставить оплату, подтвердить и завершить
state = await client.set_pending_payment(tax_request_id, state.cas_version)
state = await client.confirm_payment(tax_request_id, state.cas_version)
state = await client.mark_ready(tax_request_id, state.cas_version)
```

Прочие переходы: `request_clarification`, `decline`, `cancel`.

## Вложения

```python
uploaded = await client.upload_attachment(
    tax_request_id, content=pdf_bytes, file_name="answer.pdf", file_type="application/pdf",
)
data = await client.download_attachment(tax_request_id, uploaded.attachment_id)  # bytes
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.tax_consult.aio.TaxConsultClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.tax_consult.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.tax_consult.enums
   :members:
   :undoc-members:
```
