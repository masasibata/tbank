# Письма (`tbank.mails`)

Внутренняя переписка H2H (host-to-host): отправка входящих писем, отметка
сообщений о прочтении и получение непрочитанных писем.

- Хост: `secured-openapi.tbank.ru` (**mTLS**, `cert`). Отправка входящего письма
  дополнительно **подписывается** (`signature=HttpSignature(key_id, secret)`);
  остальное — по **Bearer**.
- Клиенты: `tbank.mails.MailsClient` (async) и `tbank.mails.sync.MailsClient` (sync).

```python
from tbank.mails import MailsClient, HttpSignature
from tbank.mails.models import IncomingMailRequest, MarkReadRequest

client = MailsClient(
    token="business-token",
    cert=("client.pem", "client-key.pem"),
    signature=HttpSignature("key-id", "secret"),   # для входящих писем
)

# отправить входящее письмо (mTLS + подпись)
await client.push_incoming_mail(IncomingMailRequest(
    external_id="EXT-1", theme_code="TAX", theme="Вопрос по НДС",
    created_at="2026-06-01T10:00:00Z", text="Здравствуйте!",
))

# непрочитанные письма и отметка о прочтении
unread = await client.list_unread()
ids = [m.id for mail in unread for m in mail.messages if m.is_unread]
await client.mark_read(MarkReadRequest(messages_ids=ids))
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.mails.aio.MailsClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.mails.models
   :members:
```
