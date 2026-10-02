from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt


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
