# Эквайринг (`tbank.acquiring`)

Интернет-эквайринг Т-Банка (EACQ): приём платежей, рекуррент, управление
клиентами и картами, СБП QR, фискализация 54-ФЗ, привязка карт.

- Хост: `https://securepay.tinkoff.ru/v2/`
- Аутентификация: [Token-подпись](authentication.md)
- Суммы: **копейки** (`int`)
- Клиенты: `tbank.acquiring.AcquiringClient` (async) и
  `tbank.acquiring.sync.AcquiringClient` (sync) — одинаковый набор методов.

## Приём платежа

```python
from tbank.acquiring import AcquiringClient
from tbank.acquiring.models import InitRequest

async with AcquiringClient(terminal_key="...", password="...") as client:
    payment = await client.init(InitRequest(amount=150000, order_id="A-1"))
    # payment.payment_url — редирект покупателя
    await client.get_state(payment.payment_id)
    await client.confirm(payment.payment_id)   # для двухстадийного
    await client.cancel(payment.payment_id)    # отмена/возврат
```

## Рекуррентные платежи

```python
# 1) при первом платеже сохраняем карту:
await client.init(InitRequest(amount=150000, order_id="A-1", customer_key="c1", recurrent="Y"))
# → RebillId придёт в вебхуке на статус AUTHORIZED

# 2) последующие списания без покупателя:
await client.charge(new_payment_id, rebill_id)
```

## Клиенты и карты

```python
await client.add_customer("c1", email="client@example.com")
cards = await client.get_card_list("c1")          # список сохранённых карт
await client.remove_card("c1", cards[0].card_id)
await client.remove_customer("c1")
```

## СБП QR

```python
from tbank.acquiring.enums import QrDataType

payment = await client.init(InitRequest(amount=150000, order_id="A-1"))
qr = await client.get_qr(payment.payment_id, data_type=QrDataType.PAYLOAD)
print(qr.data)                                    # ссылка qr.nspk.ru
banks = await client.get_qr_members(payment.payment_id)
```

СБП-рекуррент (автоплатежи по привязанному счёту):

```python
add = await client.add_account_qr("Привязка счёта")     # QR + request_key
state = await client.get_add_account_qr_state(add.request_key)  # ждём ACTIVE
await client.charge_qr(new_payment_id, state.account_token)
```

## Фискализация (54-ФЗ)

```python
from tbank.acquiring.models import Receipt, ReceiptItem
from tbank.acquiring.enums import Tax, Taxation, PaymentObject

receipt = Receipt(
    taxation=Taxation.USN_INCOME, email="client@example.com",
    items=[ReceiptItem(name="Товар", price=100000, quantity=1, amount=100000,
                       tax=Tax.VAT_22, payment_object=PaymentObject.COMMODITY)],
)
await client.init(InitRequest(amount=100000, order_id="A-1", receipt=receipt))
# двухстадийный сценарий — чек при подтверждении:
await client.send_closing_receipt(payment_id, receipt)
```

## Привязка карты (без оплаты)

```python
from tbank.acquiring.enums import CheckType

add = await client.add_card("c1", check_type=CheckType.THREE_DS)
# add.payment_url — форма ввода карты
state = await client.get_add_card_state(add.request_key)   # COMPLETED → card_id/rebill_id
```

## Клиент

```{eval-rst}
.. autoclass:: tbank.acquiring.aio.AcquiringClient
   :members:
```

## Модели

```{eval-rst}
.. automodule:: tbank.acquiring.models
   :members:
```

## Перечисления

```{eval-rst}
.. automodule:: tbank.acquiring.enums
   :members:
   :undoc-members:
```
