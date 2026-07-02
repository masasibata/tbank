# Справочник API

## Эквайринг — `tbank.acquiring`

Асинхронный клиент (`tbank.acquiring.AcquiringClient`) и синхронный
(`tbank.acquiring.sync.AcquiringClient`) имеют одинаковый набор методов.

```{eval-rst}
.. autoclass:: tbank.acquiring.aio.AcquiringClient
   :members:
```

Модели запросов и ответов — в `tbank.acquiring.models` (`InitRequest`, `Receipt`,
`ReceiptItem`, `Card`, ...), перечисления — в `tbank.acquiring.enums`
(`PaymentStatus`, `Tax`, `Taxation`, `PaymentObject`, `CheckType`, ...).

## Открытый банк — `tbank.business`

```{eval-rst}
.. autoclass:: tbank.business.aio.BusinessClient
   :members:
```

Модели — в `tbank.business.models`, перечисления — в `tbank.business.enums`.

## Ошибки — `tbank.core.errors`

```{eval-rst}
.. automodule:: tbank.core.errors
   :members:
   :show-inheritance:
```
