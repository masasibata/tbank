# Ядро (`tbank.core`)

Домен-агностичный фундамент, общий для эквайринга и открытого банка: транспорт,
стратегии аутентификации, ретраи, декларативные эндпоинты, модели и ошибки.
Обычно напрямую не используется, но полезен для тонкой настройки (свой транспорт,
таймауты, политика ретраев).

## Ошибки

```{eval-rst}
.. automodule:: tbank.core.errors
   :members:
   :show-inheritance:
```

## Ретраи

```{eval-rst}
.. automodule:: tbank.core.retry
   :members:
```

## Аутентификация

```{eval-rst}
.. automodule:: tbank.core.auth
   :members:
```

## Транспорт

```{eval-rst}
.. autoclass:: tbank.core.transport.AsyncTransport
   :members:

.. autoclass:: tbank.core.transport.SyncTransport
   :members:
```

## Модели и типы

```{eval-rst}
.. automodule:: tbank.core.models
   :members:
```

## Эндпоинты

```{eval-rst}
.. autoclass:: tbank.core.endpoint.Endpoint
   :members:
```
