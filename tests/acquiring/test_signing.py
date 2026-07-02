from tbank.acquiring.signing import build_token

DOC_TOKEN = "72dd466f8ace0a37a1f740ce5fb78101712bc0665d91a8108c7c8a0ccd426db2"


def test_matches_official_doc_vector():
    fields = {
        "TerminalKey": "MerchantTerminalKey",
        "Amount": "19200",
        "OrderId": "00000",
        "Description": "Подарочная карта на 1000 рублей",
    }
    assert build_token(fields, "11111111111111") == DOC_TOKEN


def test_int_amount_stringified_same_as_doc():
    fields = {
        "TerminalKey": "MerchantTerminalKey",
        "Amount": 19200,  # int, а не str
        "OrderId": "00000",
        "Description": "Подарочная карта на 1000 рублей",
    }
    assert build_token(fields, "11111111111111") == DOC_TOKEN


def test_nested_objects_and_arrays_excluded():
    base = {"TerminalKey": "T", "Amount": 100}
    with_nested = {**base, "Receipt": {"x": 1}, "Items": [1, 2]}
    assert build_token(base, "p") == build_token(with_nested, "p")


def test_bool_is_lowercase_true_false():
    # Ключи сортируются по алфавиту: Password < Recurrent, значит "p" + "true".
    token = build_token({"Recurrent": True}, "p")
    import hashlib

    expected = hashlib.sha256("ptrue".encode("utf-8")).hexdigest()
    assert token == expected


def test_existing_token_field_is_ignored():
    base = {"TerminalKey": "T", "Amount": 100}
    assert build_token({**base, "Token": "old"}, "p") == build_token(base, "p")
