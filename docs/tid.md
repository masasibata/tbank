# T-ID (`tbank.tid`)

T-ID — единая точка входа и идентификации Т-Банка. Пакет закрывает две части:

1. **OAuth 2.0 / OIDC** (`TidOAuth`) — «Войти через Т-Банк»: страница согласия,
   обмен кода на токены, refresh, introspect, revoke и userinfo на `id.tbank.ru`.
2. **Data-эндпоинты** (`TidClient`) — учётные данные, документы, адреса, счета,
   статусы (идентификация, самозанятость, иноагент, ПДЛ, чёрные списки),
   информация о компании (T-Business ID) и делегированная идентификация на
   `business.tbank.ru/openapi`.

- Хосты: `https://id.tbank.ru` (OAuth) и `https://business.tbank.ru/openapi` (данные).
- Аутентификация: `client_secret_basic` для OAuth; **Bearer** self-service токен
  (скоупы `opensme/...`, опционально mTLS) для data-эндпоинтов.
- Провод: `snake_case` (OAuth, по RFC/OIDC) и `camelCase` (данные T-API).
- Клиенты: `tbank.tid.TidOAuth` / `tbank.tid.TidClient` (async) и их аналоги в
  `tbank.tid.sync`.

## Вход через Т-Банк (OAuth 2.0)

```python
from tbank.tid import TidOAuth

oauth = TidOAuth(client_id="...", client_secret="...")

# 1) отправляем пользователя на страницу согласия (можно с PKCE):
url = oauth.build_authorization_url(
    redirect_uri="https://myapp.ru/auth/complete",
    scope=["openid", "phone", "profile"],
    state="csrf-token",
    code_challenge="...",           # опционально, метод по умолчанию S256
)

# 2) на redirect_uri прилетают code и state → меняем код на токены:
token = await oauth.fetch_token("the-code", "https://myapp.ru/auth/complete")
print(token.access_token, token.refresh_token, token.expires_in)

# 3) проверяем выданные скоупы и получаем данные пользователя:
intro = await oauth.introspect(token.access_token)
assert intro.active and "phone" in intro.scopes
user = await oauth.get_userinfo(token.access_token)
print(user.sub, user.phone_number)

# обновление и отзыв:
fresh = await oauth.refresh_token(token.refresh_token)
await oauth.revoke(token.refresh_token)
```

`client_credentials`-поток (сервис-сервис) — `fetch_client_credentials_token(scope=...)`.

## Учётные данные и документы

```python
from tbank.tid import TidClient
from tbank.tid.enums import IdDocumentType

async with TidClient(token="self-service-token") as client:
    user = await client.get_userinfo()          # ФИО, телефон, пол, дата рождения
    inn = await client.get_inn()
    snils = await client.get_snils()
    passport = await client.get_passport([IdDocumentType.PASSPORT])
    licenses = await client.get_driver_licenses()
    addresses = await client.get_addresses("REGISTRATION_ADDRESS")
    accounts = await client.get_debit_accounts()
```

## Статусы физлица

```python
await client.get_identification_status()   # is_identified
await client.get_self_employed_status()    # is_self_employed
await client.get_foreign_agent_status()    # is_foreign_agent
await client.get_pdl_status()              # публичное должностное лицо
await client.get_blacklist_status()        # чёрные списки
```

## Компания (T-Business ID)

```python
company = await client.get_company()               # реквизиты, банк, статус, СНО
signer = await client.get_signer_status()          # is_signer
```

## Кобренд, счётчики и подписки

```python
await client.get_cobrand(program_id=42)
await client.get_detail_counters()
await client.set_detail_counters(SetCounterRequest(count=5))
await client.get_subscription()                    # тип активной подписки
await client.get_subscription_grade()              # код подписки + грейд
```

## Делегированная идентификация

```python
await client.get_delegated_identification()                 # паспорт, адрес, флаги
await client.get_personal_data("request-uuid")              # app-сценарий
await client.get_remote_identification_result("res-secret") # web-сценарий
```

```{note}
Data-эндпоинты вызываются в максимальной доступной версии (`v2` там, где она есть;
иначе `v1`). Схемы `v1` и `v2` идентичны.
```

## Клиенты

```{eval-rst}
.. autoclass:: tbank.tid.aio.TidOAuth
   :members:

.. autoclass:: tbank.tid.aio.TidClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.tid.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.tid.enums
   :members:
   :undoc-members:
```
