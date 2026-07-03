# Работа с файлами (`tbank.files`)

Файловое хранилище: загрузка и скачивание файлов по идентификатору.

- Хост: `business.tbank.ru/openapi` по **Bearer**-токену.
- Тело файла — `application/octet-stream`; скачивание возвращает «сырые» байты.
- Клиенты: `tbank.files.FilesClient` (async) и `tbank.files.sync.FilesClient` (sync).

```python
from tbank.files import FilesClient

client = FilesClient(token="business-token")

# загрузить файл
uploaded = await client.upload_file(
    pdf_bytes, document_type="ACT", file_name="act.pdf", ttl="86400",
)

# скачать файл по идентификатору
content = await client.download_file(uploaded.file_id, document_type="ACT")
```

Если файл хранится в base64, передайте `base64_encoded=True` — заголовок
`X-Base64-Encoded` уйдёт в запрос.

## Клиент

```{eval-rst}
.. autoclass:: tbank.files.aio.FilesClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.files.models
   :members:
```
