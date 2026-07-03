# Шопинг — чаты (`tbank.shopping`)

Чаты магазина с покупателями: список чатов, история сообщений, отправка сообщений
и обмен файлами.

- Хост: `secured-openapi.tbank.ru` (**mTLS**, `cert`) по **Bearer**-токену.
- Файлы: загрузка — `application/octet-stream`, скачивание — «сырые» байты.
- Клиенты: `tbank.shopping.ShoppingClient` (async) и
  `tbank.shopping.sync.ShoppingClient` (sync).

```python
from tbank.shopping import ShoppingClient
from tbank.shopping.models import SendMessageRequest

client = ShoppingClient(
    token="business-token",
    cert=("client.pem", "client-key.pem"),
)

chats = await client.list_chats(shop_id="SHOP-1")
chat_id = chats.chats[0].chat_id

messages = await client.list_messages("SHOP-1", chat_id, limit=50)

# отправить файл, затем сообщение с этим файлом
uploaded = await client.upload_chat_file(
    "SHOP-1", chat_id, pdf_bytes, file_name="invoice.pdf", file_type="application/pdf",
)
await client.send_message("SHOP-1", chat_id, SendMessageRequest(
    partner_message_id="pm-1", file_id=uploaded.file_id,
))

# скачать файл из сообщения
content = await client.download_chat_file("SHOP-1", chat_id, uploaded.file_id)
```

`partner_message_id` — ключ идемпотентности сообщения на стороне партнёра.

## Клиент

```{eval-rst}
.. autoclass:: tbank.shopping.aio.ShoppingClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.shopping.models
   :members:
```
