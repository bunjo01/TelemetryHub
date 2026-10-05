from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest

from app.infrastructure import tokens

SECRET = "test-only-secret-" * 4
USER_ID = UUID("128a2f01-d049-43b8-98ca-afae7b78d907")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1, tzinfo=UTC)

    monkeypatch.setattr(tokens, "datetime", FrozenDatetime)
    monkeypatch.setattr(jwt.api_jwt, "datetime", FrozenDatetime)


def test_access_token_round_trip() -> None:
    token = tokens.create_access_token(USER_ID, SECRET, 15)

    assert tokens.decode_access_token(token, SECRET) == USER_ID
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert payload == {
        "sub": str(USER_ID),
        "iat": int(NOW.timestamp()),
        "exp": int((NOW + timedelta(minutes=15)).timestamp()),
    }


@pytest.mark.parametrize(
    "case",
    [
        "expired",
        "expires_now",
        "future_iat",
        "missing_sub",
        "missing_iat",
        "missing_exp",
        "invalid_sub",
        "non_string_sub",
        "string_iat",
        "float_exp",
        "bool_iat",
        "wrong_signature",
        "wrong_algorithm",
        "malformed",
    ],
)
def test_invalid_tokens_are_rejected(case: str) -> None:
    now = int(NOW.timestamp())
    payload = {"sub": str(USER_ID), "iat": now - 60, "exp": now + 900}
    signing_key = SECRET
    algorithm = "HS256"

    if case == "expired":
        payload["exp"] = now - 1
    elif case == "expires_now":
        payload["exp"] = now
    elif case == "future_iat":
        payload["iat"] = now + 1
    elif case.startswith("missing_"):
        del payload[case.removeprefix("missing_")]
    elif case == "invalid_sub":
        payload["sub"] = "not-a-uuid"
    elif case == "non_string_sub":
        payload["sub"] = 123
    elif case == "string_iat":
        payload["iat"] = str(now - 60)
    elif case == "float_exp":
        payload["exp"] = float(now + 900)
    elif case == "bool_iat":
        payload["iat"] = True
    elif case == "wrong_signature":
        signing_key = "different-test-secret-" * 4
    elif case == "wrong_algorithm":
        algorithm = "HS384"

    token = jwt.encode(payload, signing_key, algorithm=algorithm)
    if case == "malformed":
        token = "not-a-jwt"

    with pytest.raises(tokens.InvalidAccessTokenError):
        tokens.decode_access_token(token, SECRET)
