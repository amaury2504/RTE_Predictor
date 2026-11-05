import pytest
from fastapi import HTTPException

from src.auth.adapters.api.auth_dependency import CheckAuthorization
from src.auth.adapters.api.rate_limit import RateLimiter
from src.auth.application.auth_use_cases import GUEST_SUBJECT


class FakeProvider:
    def verify_token(self, token):
        return token                         # le « jeton » est directement le sujet


def test_rate_limiter_blocks_after_max_calls_then_recovers():
    now = [0.0]
    limiter = RateLimiter(max_calls=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        limiter.check("ip")
    with pytest.raises(HTTPException) as err:
        limiter.check("ip")
    assert err.value.status_code == 429 and "Retry-After" in err.value.headers
    now[0] = 61.0                            # la fenêtre est passée
    limiter.check("ip")


def test_rate_limiter_is_per_ip():
    limiter = RateLimiter(max_calls=1, window_seconds=60, clock=lambda: 0.0)
    limiter.check("a")
    limiter.check("b")
    with pytest.raises(HTTPException):
        limiter.check("a")


def test_rate_limiter_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        RateLimiter(max_calls=0, window_seconds=10)


def test_guest_is_refused_on_registered_routes_but_user_is_accepted():
    checker = CheckAuthorization(FakeProvider())
    assert checker.authorized_request(f"Bearer {GUEST_SUBJECT}") == GUEST_SUBJECT   # le profil invité peut lire
    with pytest.raises(HTTPException) as err:
        checker.registered_request(f"Bearer {GUEST_SUBJECT}")
    assert err.value.status_code == 403
    assert checker.registered_request("Bearer alice@example.com") == "alice@example.com"
