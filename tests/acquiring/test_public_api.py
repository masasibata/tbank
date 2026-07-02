def test_async_client_reexported_at_domain_root():
    from tbank.acquiring import AcquiringClient  # async — основной
    from tbank.acquiring.sync import AcquiringClient as SyncClient

    assert AcquiringClient.__module__ == "tbank.acquiring.aio"
    assert SyncClient.__module__ == "tbank.acquiring.sync"


def test_models_and_webhooks_accessible():
    from tbank.acquiring import enums, models, webhooks

    assert hasattr(models, "InitRequest")
    assert hasattr(webhooks, "verify_notification")
    assert hasattr(enums, "PaymentStatus")


def test_version_exposed():
    import tbank

    assert isinstance(tbank.__version__, str)
