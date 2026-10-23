from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_database_session
from app.api.schemas.devices import CreateDeviceRequest, DeviceResponse
from app.application.devices import (
    DeviceCompanyUnavailableError,
    DevicePermissionError,
    create_device,
)
from app.infrastructure.repositories.users import CurrentUser

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DeviceResponse,
    responses={
        401: {"description": "Invalid or missing credentials"},
        403: {"description": "Owner access or an active company required"},
        503: {"description": "Device registration temporarily unavailable"},
    },
)
def create_device_endpoint(
    payload: CreateDeviceRequest,
    response: Response,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_database_session)],
) -> DeviceResponse:
    response.headers["Cache-Control"] = "no-store"

    try:
        device = create_device(
            session=session,
            actor=current_user,
            name=payload.name,
            description=payload.description,
            device_type=payload.device_type,
        )
    except DevicePermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company owner access required.",
            headers={"Cache-Control": "no-store"},
        ) from None
    except DeviceCompanyUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company is unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device registration temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None

    return DeviceResponse(
        id=device.id,
        company_id=device.company_id,
        name=device.name,
        description=device.description,
        device_type=device.device_type,
        status=device.status,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )
