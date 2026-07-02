from tbank.core.errors import (
    InsufficientFundsError,
    TBankAPIError,
    ThreeDSError,
    build_api_error,
)


def test_known_code_maps_to_specific_exception():
    err = build_api_error(code="1051", message="нет средств")
    assert isinstance(err, InsufficientFundsError)
    assert err.code == "1051"


def test_3ds_code_maps():
    assert isinstance(build_api_error(code="101", message="x"), ThreeDSError)


def test_unknown_code_falls_back_to_base():
    err = build_api_error(code="99999", message="oops", details="d", http_status=500)
    assert type(err) is TBankAPIError
    assert err.details == "d"
    assert err.http_status == 500


def test_message_includes_code():
    assert "[1051]" in str(build_api_error(code="1051", message="нет средств"))
