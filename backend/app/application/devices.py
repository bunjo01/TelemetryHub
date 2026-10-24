from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.enums.device_types import DeviceType
from app.infrastructure.repositories.companies import (
    read_company_status_for_device_operation,
)
from app.infrastructure.repositories.devices import (
    DeviceDetails,
    DevicePage,
    insert_device,
    read_device_details,
    read_device_page,
    update_device_details,
    update_device_status,
)
from app.infrastructure.repositories.users import CurrentUser


class DevicePermissionError(Exception):
    pass


class DeviceCompanyUnavailableError(Exception):
    pass


class DeviceNotFoundError(Exception):
    pass


def create_device(
    session: Session,
    *,
    actor: CurrentUser,
    name: str,
    description: str | None,
    device_type: DeviceType,
) -> DeviceDetails:
    if (
        actor.status != "active"
        or actor.role != "company_owner"
        or actor.company_id is None
    ):
        raise DevicePermissionError

    with session.begin():
        company_status = read_company_status_for_device_operation(
            session,
            actor.company_id,
        )
        if company_status != "active":
            raise DeviceCompanyUnavailableError

        device = insert_device(
            session,
            company_id=actor.company_id,
            name=name,
            description=description,
            device_type=device_type,
        )

    return device


def get_device_details(
    session: Session,
    *,
    actor: CurrentUser,
    device_id: UUID,
) -> DeviceDetails:
    if (
        actor.status != "active"
        or actor.role not in ("company_owner", "member")
        or actor.company_id is None
    ):
        raise DevicePermissionError

    with session.begin():
        company_status = read_company_status_for_device_operation(
            session,
            actor.company_id,
        )
        if company_status != "active":
            raise DeviceCompanyUnavailableError

        device = read_device_details(
            session,
            company_id=actor.company_id,
            device_id=device_id,
        )
        if device is None:
            raise DeviceNotFoundError

    return device


def list_devices(
    session: Session,
    *,
    actor: CurrentUser,
    device_status: Literal["active", "inactive", "all"],
    search: str | None,
    limit: int,
    offset: int,
) -> DevicePage:
    if (
        actor.status != "active"
        or actor.role not in ("company_owner", "member")
        or actor.company_id is None
    ):
        raise DevicePermissionError

    with session.begin():
        company_status = read_company_status_for_device_operation(
            session,
            actor.company_id,
        )
        if company_status != "active":
            raise DeviceCompanyUnavailableError

        page = read_device_page(
            session,
            company_id=actor.company_id,
            device_status=None if device_status == "all" else device_status,
            search=search,
            limit=limit,
            offset=offset,
        )

    return page


def edit_device(
    session: Session,
    *,
    actor: CurrentUser,
    device_id: UUID,
    name: str | None,
    description: str | None,
    update_description: bool,
) -> DeviceDetails:
    if (
        actor.status != "active"
        or actor.role != "company_owner"
        or actor.company_id is None
    ):
        raise DevicePermissionError

    with session.begin():
        company_status = read_company_status_for_device_operation(
            session,
            actor.company_id,
        )
        if company_status != "active":
            raise DeviceCompanyUnavailableError

        device = update_device_details(
            session,
            company_id=actor.company_id,
            device_id=device_id,
            name=name,
            description=description,
            update_description=update_description,
        )
        if device is None:
            raise DeviceNotFoundError

    return device


def set_device_status(
    session: Session,
    *,
    actor: CurrentUser,
    device_id: UUID,
    device_status: Literal["active", "inactive"],
) -> DeviceDetails:
    if (
        actor.status != "active"
        or actor.role != "company_owner"
        or actor.company_id is None
    ):
        raise DevicePermissionError

    with session.begin():
        company_status = read_company_status_for_device_operation(
            session,
            actor.company_id,
        )
        if company_status != "active":
            raise DeviceCompanyUnavailableError

        device = update_device_status(
            session,
            company_id=actor.company_id,
            device_id=device_id,
            device_status=device_status,
        )
        if device is None:
            raise DeviceNotFoundError

    return device
