import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from time import monotonic, sleep
from uuid import UUID, uuid4

import pytest
from psycopg.errors import LockNotAvailable
from sqlalchemy import Engine, create_engine, delete, select, text, update
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
def editing_database() -> Iterator[tuple[Engine, CurrentUser, UUID]]:
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


@pytest.mark.parametrize("competitor", ["description", "name", "deactivate"])
def test_unchanged_edit_still_holds_device_and_company_locks(
    editing_database: tuple[Engine, CurrentUser, UUID],
    monkeypatch: pytest.MonkeyPatch,
    competitor: str,
) -> None:
    engine, actor, device_id = editing_database
    original_update = application.update_device_details
    with Session(engine) as first, Session(engine) as second:

        def competing_edit() -> DeviceDetails:
            return application.edit_device(
                second,
                actor=actor,
                device_id=device_id,
                name="Second name" if competitor == "name" else None,
                description="Second description",
                update_description=competitor == "description",
            )

        def update_with_competitor(
            session: Session,
            *,
            company_id: UUID,
            device_id: UUID,
            name: str | None,
            description: str | None,
            update_description: bool,
        ) -> DeviceDetails | None:
            device = original_update(
                session,
                company_id=company_id,
                device_id=device_id,
                name=name,
                description=description,
                update_description=update_description,
            )
            if session is first:
                with pytest.raises(OperationalError) as error:
                    if competitor == "deactivate":
                        with second.begin():
                            second.execute(
                                update(Company)
                                .where(Company.id == company_id)
                                .values(status="inactive")
                            )
                    else:
                        competing_edit()
                assert isinstance(error.value.orig, LockNotAvailable)
            return device

        monkeypatch.setattr(
            application, "update_device_details", update_with_competitor
        )
        application.edit_device(
            first,
            actor=actor,
            device_id=device_id,
            # No UPDATE occurs: only the explicit SELECT lock can block the competitor.
            name="Original",
            description=None,
            update_description=False,
        )
        if competitor == "deactivate":
            with second.begin():
                second.execute(
                    update(Company)
                    .where(Company.id == actor.company_id)
                    .values(status="inactive")
                )
            with pytest.raises(application.DeviceCompanyUnavailableError):
                application.edit_device(
                    first,
                    actor=actor,
                    device_id=device_id,
                    name="Rejected",
                    description=None,
                    update_description=False,
                )
        else:
            competing_edit()

        with first.begin():
            stored = first.scalar(select(Device).where(Device.id == device_id))
            assert stored is not None
            assert stored.name == (
                "Second name" if competitor == "name" else "Original"
            )
            assert stored.description == (
                "Second description"
                if competitor == "description"
                else "Original description"
            )


def test_edit_refreshes_previously_loaded_device(
    editing_database: tuple[Engine, CurrentUser, UUID],
) -> None:
    engine, actor, device_id = editing_database
    with Session(engine, expire_on_commit=False) as stale, Session(engine) as other:
        with stale.begin():
            cached = stale.get(Device, device_id)
            assert cached is not None
        application.edit_device(
            other,
            actor=actor,
            device_id=device_id,
            name="New name",
            description=None,
            update_description=False,
        )
        assert cached.name == "Original"
        result = application.edit_device(
            stale,
            actor=actor,
            device_id=device_id,
            name="Original",
            description=None,
            update_description=False,
        )
        assert result.name == "Original"
        assert result.description == "Original description"
        with other.begin():
            stored = other.get(Device, device_id)
            assert stored is not None
            assert stored.name == "Original"
            assert stored.description == "Original description"


@pytest.mark.parametrize("same_field", [False, True])
def test_waiting_edit_completes_after_commit(
    editing_database: tuple[Engine, CurrentUser, UUID], same_field: bool
) -> None:
    engine, actor, device_id = editing_database
    assert actor.company_id is not None
    worker_pid: Queue[int] = Queue()

    def edit_in_another_connection() -> DeviceDetails:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET lock_timeout = '5s'")
            pid = connection.scalar(text("SELECT pg_backend_pid()"))
            connection.commit()
            worker_pid.put(pid)
            with Session(bind=connection) as session:
                return application.edit_device(
                    session,
                    actor=actor,
                    device_id=device_id,
                    name="Second name" if same_field else None,
                    description="Second description",
                    update_description=not same_field,
                )

    # Confirm PostgreSQL sees a blocked worker before allowing the first commit;
    # do not infer concurrency from elapsed time or thread scheduling.
    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(engine) as first, first.begin():
            first_pid = first.scalar(text("SELECT pg_backend_pid()"))
            assert (
                read_company_status_for_device_operation(first, actor.company_id)
                == "active"
            )
            application.update_device_details(
                first,
                company_id=actor.company_id,
                device_id=device_id,
                name="First name",
                description=None,
                update_description=False,
            )
            future = executor.submit(edit_in_another_connection)
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
                            "Competing edit completed before the first committed"
                        )
                    if monotonic() >= deadline:
                        pytest.fail(
                            "Competing edit did not enter the expected lock wait"
                        )
                    sleep(0.01)
        result = future.result(timeout=5)

    assert result.name == ("Second name" if same_field else "First name")
    assert result.description == (
        "Original description" if same_field else "Second description"
    )
    with Session(engine) as verification:
        stored = verification.get(Device, device_id)
        assert stored is not None
        assert stored.name == result.name
        assert stored.description == result.description
