from tbank.core.auth import BearerAuth, NoAuth


def test_noauth_is_identity():
    body, headers = NoAuth().apply({"a": 1}, {"Content-Type": "application/json"})
    assert body == {"a": 1}
    assert headers == {"Content-Type": "application/json"}


def test_bearer_adds_header_and_keeps_body():
    body, headers = BearerAuth("TKN").apply({"a": 1}, {})
    assert body == {"a": 1}
    assert headers["Authorization"] == "Bearer TKN"
