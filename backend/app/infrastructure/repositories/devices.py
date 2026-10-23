from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.enums.device_types import DeviceType
from app.infrastructure.models.device import Device


@dataclass(frozen=True)
class DeviceDetails:
    id: UUID
    company_id: UUID
    name: str
    description: str | None
    device_type: DeviceType
    status: str
    created_at: datetime
    updated_at: datetime


def insert_device(
    session: Session,
    *,
    company_id: UUID,
    name: str,
    description: str | None,
    device_type: DeviceType,
) -> DeviceDetails:
    device = Device(
        company_id=company_id,
        name=name,
        description=description,
        device_type=device_type.value,
    )
    session.add(device)
    session.flush()

    return DeviceDetails(
        id=device.id,
        company_id=device.company_id,
        name=device.name,
        description=device.description,
        device_type=DeviceType(device.device_type),
        status=device.status,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )
