from tbank.core.retry import RetryPolicy, compute_delay, should_retry


def test_retries_on_5xx_until_attempts_exhausted():
    policy = RetryPolicy(attempts=3)
    assert should_retry(policy, status=503, attempt=1) is True
    assert should_retry(policy, status=503, attempt=3) is False


def test_no_retry_on_4xx_except_429():
    policy = RetryPolicy()
    assert should_retry(policy, status=400, attempt=1) is False
    assert should_retry(policy, status=429, attempt=1) is True


def test_network_error_retries():
    assert should_retry(RetryPolicy(), status=None, attempt=1) is True


def test_delay_is_exponential_without_jitter():
    policy = RetryPolicy(backoff_base=0.5, jitter=False)
    assert compute_delay(policy, attempt=1) == 0.5
    assert compute_delay(policy, attempt=2) == 1.0
    assert compute_delay(policy, attempt=3) == 2.0


def test_retry_after_is_respected_and_capped():
    policy = RetryPolicy(backoff_max=8.0, jitter=False)
    assert compute_delay(policy, attempt=1, retry_after=3.0) == 3.0
    assert compute_delay(policy, attempt=1, retry_after=100.0) == 8.0
