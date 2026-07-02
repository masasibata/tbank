import pytest

from tbank.acquiring.errors import raise_for_acquiring_result
from tbank.core.errors import InsufficientFundsError, TBankAPIError


def test_success_true_does_not_raise():
    raise_for_acquiring_result({"Success": True, "ErrorCode": "0"})


def test_known_error_code_raises_specific():
    with pytest.raises(InsufficientFundsError):
        raise_for_acquiring_result(
            {"Success": False, "ErrorCode": "1051", "Message": "нет средств"}
        )


def test_unknown_error_code_raises_base_with_fields():
    with pytest.raises(TBankAPIError) as info:
        raise_for_acquiring_result(
            {
                "Success": False,
                "ErrorCode": "5",
                "Message": "bad",
                "Details": "d",
                "Status": "REJECTED",
            }
        )
    assert info.value.status == "REJECTED"
    assert info.value.details == "d"
