from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.infrastructure.models.company import Company
from app.infrastructure.models.invitation import Invitation
from app.infrastructure.models.user import User


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
