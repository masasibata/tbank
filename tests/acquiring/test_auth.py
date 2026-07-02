from tbank.acquiring.auth import TokenSignatureAuth
from tbank.acquiring.signing import build_token


def test_apply_injects_terminal_key_and_token():
    auth = TokenSignatureAuth("MerchantTerminalKey", "11111111111111")
    body, headers = auth.apply(
        {
            "Amount": 19200,
            "OrderId": "00000",
            "Description": "Подарочная карта на 1000 рублей",
        },
        {},
    )
    assert body["TerminalKey"] == "MerchantTerminalKey"
    assert (
        body["Token"]
        == "72dd466f8ace0a37a1f740ce5fb78101712bc0665d91a8108c7c8a0ccd426db2"
    )
    assert headers == {}


def test_apply_handles_empty_body():
    body, _ = TokenSignatureAuth("T", "p").apply(None, {})
    assert body["TerminalKey"] == "T"
    assert body["Token"] == build_token({"TerminalKey": "T"}, "p")
