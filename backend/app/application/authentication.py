from uuid import UUID

from sqlalchemy.orm import Session

from app.infrastructure.passwords import verify_password
from app.infrastructure.repositories.users import (
    CurrentUser,
    find_user_by_id,
    find_user_credentials,
)


class InvalidCredentialsError(Exception):
    pass


class CurrentUserUnavailableError(Exception):
    pass


def authenticate_user(
    session: Session,
    email: str,
    password: str,
    dummy_password_hash: str,
) -> UUID:
    with session.begin():
        credentials = find_user_credentials(session, email)

    password_hash = (
        credentials.password_hash if credentials is not None else dummy_password_hash
    )
    password_matches = verify_password(password, password_hash)

    if credentials is None:
        raise InvalidCredentialsError

    if not password_matches or credentials.status != "active":
        raise InvalidCredentialsError

    return credentials.id


def load_current_user(
    session: Session,
    user_id: UUID,
) -> CurrentUser:
    with session.begin():
        user = find_user_by_id(
            session=session,
            user_id=user_id,
        )

    if user is None or user.status != "active":
        raise CurrentUserUnavailableError

    return user
