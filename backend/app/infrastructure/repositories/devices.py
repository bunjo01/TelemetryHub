from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
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


@dataclass(frozen=True)
class DevicePage:
    items: list[DeviceDetails]
    limit: int
    offset: int
    has_more: bool


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

    return _to_device_details(device)


def read_device_details(
    session: Session,
    *,
    company_id: UUID,
    device_id: UUID,
) -> DeviceDetails | None:
    statement = select(Device).where(
        Device.id == device_id,
        Device.company_id == company_id,
    )
    device = session.scalar(statement)

    if device is None:
        return None

    return _to_device_details(device)


def read_device_page(
    session: Session,
    *,
    company_id: UUID,
    device_status: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> DevicePage:
    statement = select(Device).where(Device.company_id == company_id)

    if device_status is not None:
        statement = statement.where(Device.status == device_status)

    if search:
        statement = statement.where(Device.name.icontains(search, autoescape=True))

    statement = (
        statement.order_by(Device.created_at.desc(), Device.id.desc())
        .offset(offset)
        .limit(limit + 1)
    )
    devices = session.scalars(statement).all()

    return DevicePage(
        items=[_to_device_details(device) for device in devices[:limit]],
        limit=limit,
        offset=offset,
        has_more=len(devices) > limit,
    )


def update_device_details(
    session: Session,
    *,
    company_id: UUID,
    device_id: UUID,
    name: str | None,
    description: str | None,
    update_description: bool,
) -> DeviceDetails | None:
    statement = (
        select(Device)
        .where(
            Device.id == device_id,
            Device.company_id == company_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    device = session.scalar(statement)

    if device is None:
        return None

    changed = False

    if name is not None and name != device.name:
        device.name = name
        changed = True

    if update_description and description != device.description:
        device.description = description
        changed = True

    if changed:
        session.flush()
        session.refresh(device)

    return _to_device_details(device)


def update_device_status(
    session: Session,
    *,
    company_id: UUID,
    device_id: UUID,
    device_status: Literal["active", "inactive"],
) -> DeviceDetails | None:
    statement = (
        select(Device)
        .where(
            Device.id == device_id,
            Device.company_id == company_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    device = session.scalar(statement)

    if device is None:
        return None

    if device.status != device_status:
        device.status = device_status
        session.flush()
        session.refresh(device)

    return _to_device_details(device)


def _to_device_details(device: Device) -> DeviceDetails:
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
