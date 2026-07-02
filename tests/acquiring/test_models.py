from tbank.acquiring.enums import PaymentStatus
from tbank.acquiring.models import (
    CancelRequest,
    ConfirmRequest,
    GetStateRequest,
    InitRequest,
    InitResponse,
)


def test_init_request_dumps_pascal_with_acronym_urls():
    req = InitRequest(amount=19200, order_id="A-1", success_url="http://ok")
    dumped = req.model_dump(by_alias=True, exclude_none=True)
    assert dumped == {"Amount": 19200, "OrderId": "A-1", "SuccessURL": "http://ok"}


def test_init_response_parses_status_and_payment_url():
    resp = InitResponse.model_validate(
        {
            "Success": True,
            "ErrorCode": "0",
            "PaymentId": "700",
            "Status": "NEW",
            "PaymentURL": "http://pay",
        }
    )
    assert resp.payment_id == "700"
    assert resp.status is PaymentStatus.NEW
    assert resp.payment_url == "http://pay"


def test_confirm_and_cancel_requests_minimal():
    assert ConfirmRequest(payment_id="700").model_dump(
        by_alias=True, exclude_none=True
    ) == {"PaymentId": "700"}
    assert CancelRequest(payment_id="700", amount=100).model_dump(
        by_alias=True, exclude_none=True
    ) == {"PaymentId": "700", "Amount": 100}
    assert GetStateRequest(payment_id="700").model_dump(
        by_alias=True, exclude_none=True
    ) == {"PaymentId": "700"}
