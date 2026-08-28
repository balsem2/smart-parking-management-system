import pytest
from fastapi import HTTPException

from app.services import login_rate_limit


def test_login_is_blocked_after_the_configured_failed_attempts(monkeypatch):
    key = "test-rate-limit"
    monkeypatch.setattr(login_rate_limit, "MAX_ATTEMPTS", 2)
    login_rate_limit.clear_login_attempts(key)

    login_rate_limit.record_failed_login(key)
    login_rate_limit.record_failed_login(key)

    with pytest.raises(HTTPException) as error:
        login_rate_limit.ensure_login_allowed(key)

    assert error.value.status_code == 429
    login_rate_limit.clear_login_attempts(key)
