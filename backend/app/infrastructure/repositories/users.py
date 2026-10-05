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


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    company_id: UUID | None
    email: str
    role: str
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


def find_user_by_id(
    session: Session,
    user_id: UUID,
) -> CurrentUser | None:
    statement = select(
        User.id,
        User.company_id,
        User.email,
        User.role,
        User.status,
    ).where(User.id == user_id)

    row = session.execute(statement).one_or_none()

    if row is None:
        return None

    user_id, company_id, email, role, status = row

    return CurrentUser(
        id=user_id,
        company_id=company_id,
        email=email,
        role=role,
        status=status,
    )
