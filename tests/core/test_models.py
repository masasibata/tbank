from decimal import Decimal

from pydantic import Field

from tbank.core.models import TBankModel, to_kopecks, to_rubles


class _Sample(TBankModel):
    order_id: str
    payment_url: str = Field(default="", alias="PaymentURL")


def test_alias_generator_produces_pascal_case():
    dumped = _Sample(order_id="A-1").model_dump(by_alias=True, exclude_none=True)
    assert dumped["OrderId"] == "A-1"


def test_explicit_alias_wins_over_generator():
    obj = _Sample.model_validate({"OrderId": "A-1", "PaymentURL": "http://p"})
    assert obj.payment_url == "http://p"
    assert obj.model_dump(by_alias=True)["PaymentURL"] == "http://p"


def test_money_helpers():
    assert to_kopecks(Decimal("100.00")) == 10000
    assert to_kopecks("192.00") == 19200
    assert to_rubles(19200) == Decimal("192.00")
