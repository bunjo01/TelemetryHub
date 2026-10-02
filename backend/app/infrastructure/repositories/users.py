from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models.user import User


@dataclass(frozen=True)
class UserCredentials:
    id: UUID
    password_hash: str = field(repr=False)
    status: str


def find_user_credentials(
    session: Session,
    email: str,
) -> UserCredentials | None:
    statement = select(
        User.id,
        User.password_hash,
        User.status,
    ).where(User.email == email)

    row = session.execute(statement).one_or_none()

    if row is None:
        return None

    user_id, password_hash, status = row

    return UserCredentials(id=user_id, password_hash=password_hash, status=status)
