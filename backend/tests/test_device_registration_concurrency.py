import os
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from psycopg.errors import LockNotAvailable
from sqlalchemy import Engine, create_engine, delete, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.application import devices as application
from app.enums.device_types import DeviceType
from app.infrastructure.models.company import Company
from app.infrastructure.models.device import Device
from app.infrastructure.repositories.devices import DeviceDetails
from app.infrastructure.repositories.users import CurrentUser


@pytest.fixture
def company_database() -> Iterator[tuple[Engine, CurrentUser]]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL test database")
    engine = create_engine(
        url,
        hide_parameters=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c statement_timeout=5000 -c lock_timeout=500",
        },
    )
    company_id = uuid4()
    actor = CurrentUser(
        uuid4(), company_id, "owner@example.com", "company_owner", "active"
    )
    try:
        with Session(engine) as session, session.begin():
            session.add(Company(id=company_id, name="Device concurrency test"))
        yield engine, actor
    finally:
        try:
            with Session(engine) as session, session.begin():
                session.execute(delete(Device).where(Device.company_id == company_id))
                session.execute(delete(Company).where(Company.id == company_id))
        finally:
            engine.dispose()


@pytest.mark.parametrize("competing_operation", ["deactivate", "register"])
def test_company_lock_during_registration(
    company_database: tuple[Engine, CurrentUser],
    monkeypatch: pytest.MonkeyPatch,
    competing_operation: str,
) -> None:
    engine, actor = company_database
    original_insert = application.insert_device

    with Session(engine) as first, Session(engine) as second:

        def insert_with_competing_operation(
            session: Session,
            *,
            company_id: UUID,
            name: str,
            description: str | None,
            device_type: DeviceType,
        ) -> DeviceDetails:
            device = original_insert(
                session,
                company_id=company_id,
                name=name,
                description=description,
                device_type=device_type,
            )
            if session is not first:
                return device

            # The first registration has inserted but has not committed yet.
            if competing_operation == "deactivate":
                with pytest.raises(OperationalError) as error:
                    with second.begin():
                        second.execute(
                            update(Company)
                            .where(Company.id == company_id)
                            .values(status="inactive")
                        )
                assert isinstance(error.value.orig, LockNotAvailable)
            else:
                application.create_device(
                    second,
                    actor=actor,
                    name="Concurrent sensor",
                    description=None,
                    device_type=DeviceType.TEMPERATURE_SENSOR,
                )
            return device

        monkeypatch.setattr(
            application, "insert_device", insert_with_competing_operation
        )
        application.create_device(
            first,
            actor=actor,
            name="First sensor",
            description=None,
            device_type=DeviceType.TEMPERATURE_SENSOR,
        )

        if competing_operation == "deactivate":
            # Once registration commits, the company update must succeed.
            with second.begin():
                second.execute(
                    update(Company)
                    .where(Company.id == actor.company_id)
                    .values(status="inactive")
                )
            with pytest.raises(application.DeviceCompanyUnavailableError):
                application.create_device(
                    first,
                    actor=actor,
                    name="Rejected sensor",
                    description=None,
                    device_type=DeviceType.TEMPERATURE_SENSOR,
                )

        with first.begin():
            names = first.scalars(
                select(Device.name)
                .where(Device.company_id == actor.company_id)
                .order_by(Device.name)
            ).all()
            expected = (
                ["First sensor"]
                if competing_operation == "deactivate"
                else ["Concurrent sensor", "First sensor"]
            )
            assert names == expected
