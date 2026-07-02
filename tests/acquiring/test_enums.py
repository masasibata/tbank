from tbank.acquiring.enums import PaymentStatus


def test_status_parsed_from_wire_value():
    assert PaymentStatus("CONFIRMED") is PaymentStatus.CONFIRMED
    assert PaymentStatus.NEW.value == "NEW"
