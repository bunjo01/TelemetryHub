import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.passwords import hash_password
from app.infrastructure.repositories import invitations as repository
from app.infrastructure.repositories.users import CurrentUser


class CompanyNotFoundError(Exception):
    pass


class InvitationConflictError(Exception):
    pass


class InvalidInvitationError(Exception):
    pass


def require_usable_invitation(
    invitation: repository.InvitationDetails | None, now: datetime
) -> repository.InvitationDetails:
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.role != "company_owner"
        or not invitation.created_at <= now < invitation.expires_at
    ):
        raise InvalidInvitationError
    return invitation


def accept_owner_invitation(session: Session, token: str, password: str) -> CurrentUser:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    # Reject unusable tokens before paying the password-hashing cost.
    with session.begin():
        invitation = require_usable_invitation(
            repository.find_invitation(session, token_hash), datetime.now(UTC)
        )
    company_id = invitation.company_id
    password_hash = hash_password(password)

    try:
        with session.begin():
            # Same lock order as creation: company first, then invitation.
            company_status = repository.lock_company_status(session, company_id)
            invitation = require_usable_invitation(
                repository.find_invitation(session, token_hash, for_update=True),
                datetime.now(UTC),
            )
            if invitation.company_id != company_id:
                raise InvalidInvitationError
            if company_status != "active":
                raise InvitationConflictError("Company is unavailable.")
            if repository.company_has_owner(session, company_id):
                raise InvitationConflictError("Company already has an owner.")
            if repository.email_has_account(session, invitation.email):
                raise InvitationConflictError("Email already has an account.")

            user = repository.insert_owner(
                session, company_id, invitation.email, password_hash
            )
            # An insert may wait for another writer; check expiration again.
            accepted_at = datetime.now(UTC)
            require_usable_invitation(invitation, accepted_at)
            repository.mark_invitation_accepted(session, invitation.id, accepted_at)
    except IntegrityError as error:
        if isinstance(
            error.orig, UniqueViolation
        ) and error.orig.diag.constraint_name in (
            "uq_users_email",
            "uq_users_company_owner",
        ):
            raise InvitationConflictError(
                "Account or company owner already exists."
            ) from error
        raise
    return user


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
