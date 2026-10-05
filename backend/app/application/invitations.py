import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.infrastructure.repositories import invitations as repository


class CompanyNotFoundError(Exception):
    pass


class InvitationConflictError(Exception):
    pass


@dataclass(frozen=True)
class CreatedOwnerInvitation:
    id: UUID
    company_id: UUID
    email: str
    expires_at: datetime
    token: str = field(repr=False)


def create_owner_invitation(
    session: Session,
    company_id: UUID,
    invited_by_id: UUID,
    email: str,
    expires_in_hours: int,
) -> CreatedOwnerInvitation:
    with session.begin():
        # All owner-invitation writers must lock this row before checking.
        company_status = repository.lock_company_status(session, company_id)
        if company_status is None:
            raise CompanyNotFoundError
        if company_status != "active":
            raise InvitationConflictError("Company is inactive.")
        if repository.company_has_owner(session, company_id):
            raise InvitationConflictError("Company already has an owner.")
        if repository.email_has_account(session, email):
            raise InvitationConflictError("Email already has an account.")

        now = datetime.now(UTC)
        if repository.has_pending_owner_invitation(session, company_id, now):
            raise InvitationConflictError(
                "Company already has a pending owner invitation."
            )

        token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(hours=expires_in_hours)
        invitation_id = repository.insert_owner_invitation(
            session=session,
            company_id=company_id,
            invited_by_id=invited_by_id,
            email=email,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            created_at=now,
            expires_at=expires_at,
        )

    return CreatedOwnerInvitation(invitation_id, company_id, email, expires_at, token)
