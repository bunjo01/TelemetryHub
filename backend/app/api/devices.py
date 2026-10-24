from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_database_session
from app.api.schemas.devices import (
    CreateDeviceRequest,
    DeviceListQuery,
    DeviceListResponse,
    DeviceResponse,
    UpdateDeviceRequest,
)
from app.application.devices import (
    DeviceCompanyUnavailableError,
    DeviceNotFoundError,
    DevicePermissionError,
    create_device,
    edit_device,
    get_device_details,
    list_devices,
    set_device_status,
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

    return DeviceResponse.model_validate(device, from_attributes=True)


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    responses={
        401: {"description": "Invalid or missing credentials"},
        403: {
            "description": "Company owner or member access and an active company required"
        },
        404: {"description": "Device not found"},
        503: {"description": "Device details temporarily unavailable"},
    },
)
def get_device_details_endpoint(
    device_id: UUID,
    response: Response,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_database_session)],
) -> DeviceResponse:
    response.headers["Cache-Control"] = "no-store"

    try:
        device = get_device_details(
            session=session,
            actor=current_user,
            device_id=device_id,
        )
    except DevicePermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company owner or member access required.",
            headers={"Cache-Control": "no-store"},
        ) from None
    except DeviceCompanyUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company is unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None
    except DeviceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found.",
            headers={"Cache-Control": "no-store"},
        ) from None
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device details temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None

    return DeviceResponse.model_validate(device, from_attributes=True)


@router.get(
    "",
    response_model=DeviceListResponse,
    responses={
        401: {"description": "Invalid or missing credentials"},
        403: {
            "description": "Company owner or member access and an active company required"
        },
        503: {"description": "Device listing temporarily unavailable"},
    },
)
def list_devices_endpoint(
    query: Annotated[DeviceListQuery, Query()],
    response: Response,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_database_session)],
) -> DeviceListResponse:
    response.headers["Cache-Control"] = "no-store"

    try:
        page = list_devices(
            session=session,
            actor=current_user,
            device_status=query.status,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )
    except DevicePermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company owner or member access required.",
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
            detail="Device listing temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None

    return DeviceListResponse(
        items=[
            DeviceResponse.model_validate(device, from_attributes=True)
            for device in page.items
        ],
        limit=page.limit,
        offset=page.offset,
        has_more=page.has_more,
    )


@router.patch(
    "/{device_id}",
    response_model=DeviceResponse,
    responses={
        401: {"description": "Invalid or missing credentials"},
        403: {"description": "Owner access and an active company required"},
        404: {"description": "Device not found"},
        503: {"description": "Device editing temporarily unavailable"},
    },
)
def edit_device_endpoint(
    device_id: UUID,
    payload: UpdateDeviceRequest,
    response: Response,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_database_session)],
) -> DeviceResponse:
    response.headers["Cache-Control"] = "no-store"

    try:
        device = edit_device(
            session=session,
            actor=current_user,
            device_id=device_id,
            name=payload.name,
            description=payload.description,
            update_description="description" in payload.model_fields_set,
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
    except DeviceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found.",
            headers={"Cache-Control": "no-store"},
        ) from None
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device editing temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None

    return DeviceResponse.model_validate(device, from_attributes=True)


@router.post(
    "/{device_id}/activate",
    response_model=DeviceResponse,
    responses={
        401: {"description": "Invalid or missing credentials"},
        403: {"description": "Owner access and an active company required"},
        404: {"description": "Device not found"},
        503: {"description": "Device status change temporarily unavailable"},
    },
)
def activate_device_endpoint(
    device_id: UUID,
    response: Response,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_database_session)],
) -> DeviceResponse:
    return _set_device_status_response(
        session=session,
        actor=current_user,
        device_id=device_id,
        device_status="active",
        response=response,
    )


@router.post(
    "/{device_id}/deactivate",
    response_model=DeviceResponse,
    responses={
        401: {"description": "Invalid or missing credentials"},
        403: {"description": "Owner access and an active company required"},
        404: {"description": "Device not found"},
        503: {"description": "Device status change temporarily unavailable"},
    },
)
def deactivate_device_endpoint(
    device_id: UUID,
    response: Response,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_database_session)],
) -> DeviceResponse:
    return _set_device_status_response(
        session=session,
        actor=current_user,
        device_id=device_id,
        device_status="inactive",
        response=response,
    )


def _set_device_status_response(
    *,
    session: Session,
    actor: CurrentUser,
    device_id: UUID,
    device_status: Literal["active", "inactive"],
    response: Response,
) -> DeviceResponse:
    response.headers["Cache-Control"] = "no-store"

    try:
        device = set_device_status(
            session=session,
            actor=actor,
            device_id=device_id,
            device_status=device_status,
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
    except DeviceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found.",
            headers={"Cache-Control": "no-store"},
        ) from None
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device status change temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None

    return DeviceResponse.model_validate(device, from_attributes=True)
