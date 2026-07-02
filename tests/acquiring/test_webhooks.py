from tbank.acquiring.enums import PaymentStatus
from tbank.acquiring.signing import build_token
from tbank.acquiring.webhooks import parse_notification, verify_notification


def _signed(password: str) -> dict:
    data = {
        "TerminalKey": "T",
        "OrderId": "A-1",
        "Success": True,
        "Status": "CONFIRMED",
        "PaymentId": 700,
        "ErrorCode": "0",
        "Amount": 19200,
    }
    data["Token"] = build_token(data, password)
    return data


def test_parse_returns_typed_notification():
    note = parse_notification(_signed("p"))
    assert note.status is PaymentStatus.CONFIRMED
    assert note.payment_id == 700
    assert note.amount == 19200


def test_verify_true_for_correct_token():
    assert verify_notification(_signed("p"), "p") is True


def test_verify_false_for_wrong_password():
    assert verify_notification(_signed("p"), "wrong") is False


def test_verify_false_when_tampered():
    data = _signed("p")
    data["Amount"] = 1
    assert verify_notification(data, "p") is False
