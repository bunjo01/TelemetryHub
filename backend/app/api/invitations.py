from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_database_session,
    get_settings,
    require_system_admin,
)
from app.api.schemas.invitations import (
    CreateOwnerInvitationRequest,
    OwnerInvitationResponse,
)
from app.application.invitations import (
    CompanyNotFoundError,
    InvitationConflictError,
    create_owner_invitation,
)
from app.config import Settings
from app.infrastructure.repositories.users import CurrentUser

router = APIRouter(prefix="/companies", tags=["invitations"])


@router.post(
    "/{company_id}/owner-invitations",
    status_code=status.HTTP_201_CREATED,
    response_model=OwnerInvitationResponse,
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Administrator access required"},
        404: {"description": "Company not found"},
        409: {"description": "Invitation conflicts with current state"},
        503: {"description": "Invitation creation unavailable"},
    },
)
def create_owner_invitation_endpoint(
    company_id: UUID,
    payload: CreateOwnerInvitationRequest,
    response: Response,
    admin: Annotated[CurrentUser, Depends(require_system_admin)],
    session: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OwnerInvitationResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        invitation = create_owner_invitation(
            session=session,
            company_id=company_id,
            invited_by_id=admin.id,
            email=str(payload.email),
            expires_in_hours=settings.invitation_expire_hours,
        )
    except CompanyNotFoundError:
        raise HTTPException(404, "Company not found.") from None
    except InvitationConflictError as error:
        raise HTTPException(409, str(error)) from None
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            503, "Invitation creation temporarily unavailable."
        ) from None

    return OwnerInvitationResponse(
        id=invitation.id,
        company_id=invitation.company_id,
        email=invitation.email,
        expires_at=invitation.expires_at,
        token=invitation.token,
    )
