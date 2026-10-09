from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
    get_database_session,
    get_settings,
    require_invitation_acceptance_capacity,
    require_system_admin,
)
from app.api.schemas.auth import UserResponse
from app.api.schemas.invitations import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    MemberInvitationResponse,
    OwnerInvitationResponse,
    PreviewInvitationRequest,
    PreviewInvitationResponse,
)
from app.application.invitations import (
    CompanyNotFoundError,
    InvalidInvitationError,
    InvitationConflictError,
    InvitationPermissionError,
    accept_invitation,
    create_member_invitation,
    create_owner_invitation,
    preview_invitation,
)
from app.config import Settings
from app.infrastructure.repositories.users import CurrentUser

router = APIRouter(prefix="/companies", tags=["invitations"])
acceptance_router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post(
    "/{company_id}/member-invitations",
    status_code=201,
    response_model=MemberInvitationResponse,
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Owner access to this company required"},
        404: {"description": "Company not found"},
        409: {"description": "Invitation conflicts with current state"},
        503: {"description": "Invitation creation unavailable"},
    },
)
def create_member_invitation_endpoint(
    company_id: UUID,
    payload: CreateInvitationRequest,
    response: Response,
    owner: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MemberInvitationResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        invitation = create_member_invitation(
            session=session,
            company_id=company_id,
            owner=owner,
            email=str(payload.email),
            expires_in_hours=settings.invitation_expire_hours,
        )
    except InvitationPermissionError:
        raise HTTPException(403, "Company owner access required.") from None
    except CompanyNotFoundError:
        raise HTTPException(404, "Company not found.") from None
    except InvitationConflictError as error:
        raise HTTPException(409, str(error)) from None
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            503, "Invitation creation temporarily unavailable."
        ) from None
    return MemberInvitationResponse(
        id=invitation.id,
        company_id=invitation.company_id,
        email=invitation.email,
        expires_at=invitation.expires_at,
        token=invitation.token,
    )


@acceptance_router.post(
    "/accept",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    dependencies=[Depends(require_invitation_acceptance_capacity)],
    responses={
        400: {"description": "Invalid, expired, or used invitation"},
        409: {"description": "Account or company conflict"},
        503: {"description": "Invitation acceptance unavailable"},
    },
)
def accept_invitation_endpoint(
    payload: AcceptInvitationRequest,
    response: Response,
    session: Annotated[Session, Depends(get_database_session)],
) -> UserResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        user = accept_invitation(
            session=session,
            token=payload.token.get_secret_value(),
            password=payload.password.get_secret_value(),
        )
    except InvalidInvitationError:
        raise HTTPException(
            400, "Invalid or expired invitation.", headers={"Cache-Control": "no-store"}
        ) from None
    except InvitationConflictError as error:
        raise HTTPException(
            409, str(error), headers={"Cache-Control": "no-store"}
        ) from None
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            503,
            "Invitation acceptance temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None
    return UserResponse(
        id=user.id,
        company_id=user.company_id,
        email=user.email,
        role=user.role,
        status=user.status,
    )


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
    payload: CreateInvitationRequest,
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


@acceptance_router.post(
    "/preview",
    response_model=PreviewInvitationResponse,
    responses={
        400: {"description": "Invalid, expired, or used invitation"},
        503: {"description": "Invitation preview unavailable"},
    },
)
def preview_invitation_endpoint(
    payload: PreviewInvitationRequest,
    response: Response,
    session: Annotated[Session, Depends(get_database_session)],
) -> PreviewInvitationResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        preview = preview_invitation(
            session=session, token=payload.token.get_secret_value()
        )
    except InvalidInvitationError:
        raise HTTPException(
            400, "Invalid or expired invitation.", headers={"Cache-Control": "no-store"}
        ) from None
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            503,
            "Invitation preview temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None
    return PreviewInvitationResponse(email=preview.email, expires_at=preview.expires_at)
