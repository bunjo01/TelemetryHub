from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt


class InvalidAccessTokenError(Exception):
    pass


def create_access_token(
    user_id: UUID,
    secret_key: str,
    expires_in_minutes: int,
) -> str:
    now = datetime.now(UTC)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=expires_in_minutes),
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm="HS256",
    )


def decode_access_token(token: str, secret_key: str) -> UUID:
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )

        # Example sub: "128a2f01-d049-43b8-98ca-afae7b78d907"
        subject = payload["sub"]

        if not isinstance(subject, str):
            raise InvalidAccessTokenError

        # Our token issuer produces integer Unix timestamps.
        issued_at = payload["iat"]
        expires_at = payload["exp"]

        if type(issued_at) is not int or type(expires_at) is not int:
            raise InvalidAccessTokenError

        if expires_at <= issued_at:
            raise InvalidAccessTokenError

        return UUID(subject)

    except (jwt.InvalidTokenError, ValueError) as error:
        raise InvalidAccessTokenError from error
