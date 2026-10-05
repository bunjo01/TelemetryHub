from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session

from app.infrastructure.models.company import Company
from app.infrastructure.models.invitation import Invitation
from app.infrastructure.models.user import User
from app.infrastructure.repositories.users import CurrentUser


@dataclass(frozen=True)
class InvitationDetails:
    id: UUID
    company_id: UUID
    email: str
    role: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None


def find_invitation(
    session: Session, token_hash: str, *, for_update: bool = False
) -> InvitationDetails | None:
    statement = select(
        Invitation.id,
        Invitation.company_id,
        Invitation.email,
        Invitation.role,
        Invitation.created_at,
        Invitation.expires_at,
        Invitation.accepted_at,
    ).where(Invitation.token_hash == token_hash)
    if for_update:
        statement = statement.with_for_update()
    row = session.execute(statement).one_or_none()
    return InvitationDetails(*row) if row is not None else None


def insert_owner(
    session: Session, company_id: UUID, email: str, password_hash: str
) -> CurrentUser:
    user = User(
        company_id=company_id,
        email=email,
        password_hash=password_hash,
        role="company_owner",
        status="active",
    )
    session.add(user)
    session.flush()
    return CurrentUser(user.id, user.company_id, user.email, user.role, user.status)


def mark_invitation_accepted(
    session: Session, invitation_id: UUID, accepted_at: datetime
) -> None:
    session.execute(
        update(Invitation)
        .where(Invitation.id == invitation_id)
        .values(accepted_at=accepted_at)
    )


def lock_company_status(session: Session, company_id: UUID) -> str | None:
    return session.scalar(
        select(Company.status).where(Company.id == company_id).with_for_update()
    )


def company_has_owner(session: Session, company_id: UUID) -> bool:
    return bool(
        session.scalar(
            select(
                exists().where(
                    User.company_id == company_id, User.role == "company_owner"
                )
            )
        )
    )


def email_has_account(session: Session, email: str) -> bool:
    return bool(session.scalar(select(exists().where(User.email == email))))


def has_pending_owner_invitation(
    session: Session, company_id: UUID, now: datetime
) -> bool:
    return bool(
        session.scalar(
            select(
                exists().where(
                    Invitation.company_id == company_id,
                    Invitation.role == "company_owner",
                    Invitation.accepted_at.is_(None),
                    Invitation.expires_at > now,
                )
            )
        )
    )


def insert_owner_invitation(
    session: Session,
    company_id: UUID,
    invited_by_id: UUID,
    email: str,
    token_hash: str,
    created_at: datetime,
    expires_at: datetime,
) -> UUID:
    invitation = Invitation(
        company_id=company_id,
        invited_by_id=invited_by_id,
        email=email,
        role="company_owner",
        token_hash=token_hash,
        created_at=created_at,
        expires_at=expires_at,
    )
    session.add(invitation)
    session.flush()
    return invitation.id
