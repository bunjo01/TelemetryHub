import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from time import monotonic, sleep
from typing import Literal
from uuid import UUID, uuid4

import pytest
from psycopg.errors import LockNotAvailable
from sqlalchemy import Engine, create_engine, delete, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.application import devices as application
from app.infrastructure.models.company import Company
from app.infrastructure.models.device import Device
from app.infrastructure.repositories.companies import (
    read_company_status_for_device_operation,
)
from app.infrastructure.repositories.devices import DeviceDetails
from app.infrastructure.repositories.users import CurrentUser


@pytest.fixture
def status_database() -> Iterator[tuple[Engine, CurrentUser, UUID]]:
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
    device_id = uuid4()
    actor = CurrentUser(
        uuid4(), company_id, "owner@example.com", "company_owner", "active"
    )
    try:
        with Session(engine) as session, session.begin():
            session.add(Company(id=company_id, name="Device concurrency test"))
            session.flush()
            session.add(
                Device(
                    id=device_id,
                    company_id=company_id,
                    name="Original",
                    description="Original description",
                    device_type="temperature_sensor",
                )
            )
        yield engine, actor, device_id
    finally:
        try:
            with Session(engine) as session, session.begin():
                session.execute(delete(Device).where(Device.company_id == company_id))
                session.execute(delete(Company).where(Company.id == company_id))
        finally:
            engine.dispose()


@pytest.mark.parametrize("competitor", ["status", "edit", "company_deactivation"])
def test_unchanged_status_request_holds_device_and_company_locks(
    status_database: tuple[Engine, CurrentUser, UUID],
    monkeypatch: pytest.MonkeyPatch,
    competitor: str,
) -> None:
    engine, actor, device_id = status_database
    original_update = application.update_device_status
    with Session(engine) as first, Session(engine) as second:

        def competing_write() -> None:
            if competitor == "company_deactivation":
                with second.begin():
                    second.execute(
                        update(Company)
                        .where(Company.id == actor.company_id)
                        .values(status="inactive")
                    )
            elif competitor == "status":
                application.set_device_status(
                    second, actor=actor, device_id=device_id, device_status="inactive"
                )
            else:
                application.edit_device(
                    second,
                    actor=actor,
                    device_id=device_id,
                    name="Edited",
                    description=None,
                    update_description=False,
                )

        def update_with_competitor(
            session: Session,
            *,
            company_id: UUID,
            device_id: UUID,
            device_status: Literal["active", "inactive"],
        ) -> DeviceDetails | None:
            device = original_update(
                session,
                company_id=company_id,
                device_id=device_id,
                device_status=device_status,
            )
            if session is first:
                with pytest.raises(OperationalError) as error:
                    competing_write()
                assert isinstance(error.value.orig, LockNotAvailable)
            return device

        with monkeypatch.context() as patch:
            patch.setattr(application, "update_device_status", update_with_competitor)
            # No UPDATE: the explicit SELECT lock must protect this no-op.
            result = application.set_device_status(
                first, actor=actor, device_id=device_id, device_status="active"
            )
        assert result.status == "active"
        competing_write()
        if competitor == "company_deactivation":
            with pytest.raises(application.DeviceCompanyUnavailableError):
                application.set_device_status(
                    first, actor=actor, device_id=device_id, device_status="inactive"
                )
        with Session(engine) as verification:
            stored = verification.get(Device, device_id)
            assert stored is not None
            assert stored.status == ("inactive" if competitor == "status" else "active")
            assert stored.name == ("Edited" if competitor == "edit" else "Original")


def test_status_change_refreshes_previously_loaded_device(
    status_database: tuple[Engine, CurrentUser, UUID],
) -> None:
    engine, actor, device_id = status_database
    with Session(engine, expire_on_commit=False) as stale, Session(engine) as other:
        with stale.begin():
            cached = stale.get(Device, device_id)
            assert cached is not None
        application.set_device_status(
            other, actor=actor, device_id=device_id, device_status="inactive"
        )
        assert cached.status == "active"
        result = application.set_device_status(
            stale, actor=actor, device_id=device_id, device_status="active"
        )
        assert result.status == "active"
        with Session(engine) as verification:
            stored = verification.get(Device, device_id)
            assert stored is not None
            assert stored.status == "active"


@pytest.mark.parametrize(
    "order", ["status_then_status", "status_then_edit", "edit_then_status"]
)
def test_waiting_write_preserves_changes_and_requested_status(
    status_database: tuple[Engine, CurrentUser, UUID], order: str
) -> None:
    engine, actor, device_id = status_database
    assert actor.company_id is not None
    worker_pid: Queue[int] = Queue()

    def write_in_another_connection() -> DeviceDetails:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET lock_timeout = '5s'")
            pid = connection.scalar(text("SELECT pg_backend_pid()"))
            connection.commit()
            worker_pid.put(pid)
            with Session(bind=connection) as session:
                if order == "status_then_edit":
                    return application.edit_device(
                        session,
                        actor=actor,
                        device_id=device_id,
                        name="Edited",
                        description=None,
                        update_description=False,
                    )
                return application.set_device_status(
                    session,
                    actor=actor,
                    device_id=device_id,
                    device_status="active"
                    if order == "status_then_status"
                    else "inactive",
                )

    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(engine) as first, first.begin():
            first_pid = first.scalar(text("SELECT pg_backend_pid()"))
            assert (
                read_company_status_for_device_operation(first, actor.company_id)
                == "active"
            )
            if order == "edit_then_status":
                application.update_device_details(
                    first,
                    company_id=actor.company_id,
                    device_id=device_id,
                    name="Edited",
                    description=None,
                    update_description=False,
                )
            else:
                application.update_device_status(
                    first,
                    company_id=actor.company_id,
                    device_id=device_id,
                    device_status="inactive",
                )
            future = executor.submit(write_in_another_connection)
            pid = worker_pid.get(timeout=3)
            deadline = monotonic() + 3
            with engine.connect() as observer:
                while True:
                    blockers = observer.scalar(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": pid}
                    )
                    if first_pid in blockers:
                        break
                    if future.done():
                        future.result()
                        pytest.fail(
                            "Competing write completed before the first committed"
                        )
                    if monotonic() >= deadline:
                        pytest.fail(
                            "Competing write did not enter the expected lock wait"
                        )
                    sleep(0.01)
        result = future.result(timeout=5)

    assert result.status == ("active" if order == "status_then_status" else "inactive")
    assert result.name == ("Original" if order == "status_then_status" else "Edited")
    assert result.description == "Original description"
    with Session(engine) as verification:
        stored = verification.get(Device, device_id)
        assert stored is not None
        assert stored.status == result.status
        assert stored.name == result.name
        assert stored.description == result.description
