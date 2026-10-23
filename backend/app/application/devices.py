from sqlalchemy.orm import Session

from app.enums.device_types import DeviceType
from app.infrastructure.repositories.companies import (
    read_company_status_for_device_operation,
)
from app.infrastructure.repositories.devices import DeviceDetails, insert_device
from app.infrastructure.repositories.users import CurrentUser


class DevicePermissionError(Exception):
    pass


class DeviceCompanyUnavailableError(Exception):
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
