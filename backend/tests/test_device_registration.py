from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api import dependencies
from app.api.devices import router
from app.application import devices as application
from app.config import Settings
from app.enums.device_types import DeviceType
from app.infrastructure.models.company import Company
from app.infrastructure.models.device import Device
from app.infrastructure.models.user import User
from app.infrastructure.repositories.devices import DeviceDetails
from app.infrastructure.tokens import create_access_token
from app.main import handle_request_validation_error

SECRET = "device-registration-test-secret-" * 3
COMPANY_ID = uuid4()
OTHER_COMPANY_ID = uuid4()
USER_ID = uuid4()

PAYLOAD = {
    "name": "  Freezer sensor 01  ",
    "device_type": "temperature_sensor",
}


@pytest.fixture
def client(database_session: Session) -> Iterator[TestClient]:
    with database_session.begin():
        database_session.add_all(
            [
                Company(id=COMPANY_ID, name="Device test company"),
                Company(id=OTHER_COMPANY_ID, name="Other device test company"),
            ]
        )
        database_session.flush()
        database_session.add(
            User(
                id=USER_ID,
                company_id=COMPANY_ID,
                email=f"{USER_ID}@example.com",
                password_hash="test-only",
                role="company_owner",
            )
        )

    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(
        RequestValidationError,
        handle_request_validation_error,
    )
    settings = Settings.model_construct(jwt_secret_key=SecretStr(SECRET))

    def get_session() -> Iterator[Session]:
        yield database_session

    app.dependency_overrides[dependencies.get_database_session] = get_session
    app.dependency_overrides[dependencies.get_settings] = lambda: settings

    token = create_access_token(USER_ID, SECRET, 15)
    with TestClient(
        app,
        headers={"Authorization": f"Bearer {token}"},
    ) as test_client:
        yield test_client


def assert_no_devices(session: Session) -> None:
    with session.begin():
        ids = session.scalars(
            select(Device.id).where(
                Device.company_id.in_([COMPANY_ID, OTHER_COMPANY_ID])
            )
        ).all()
        assert ids == []


@pytest.mark.parametrize(
    "device_type",
    ["temperature_sensor", "environment_sensor", "gps_tracker"],
)
def test_owner_registers_device(
    client: TestClient,
    database_session: Session,
    device_type: str,
) -> None:
    response = client.post(
        "/devices",
        json={**PAYLOAD, "device_type": device_type},
    )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["company_id"] == str(COMPANY_ID)
    assert body["name"] == "Freezer sensor 01"
    assert body["description"] is None
    assert body["device_type"] == device_type
    assert body["status"] == "active"
    assert body["created_at"]
    assert body["updated_at"]

    with database_session.begin():
        device = database_session.get(Device, UUID(body["id"]))
        assert device is not None
        assert device.company_id == COMPANY_ID
        assert device.name == body["name"]
        assert device.device_type == device_type
        assert device.status == "active"


@pytest.mark.parametrize("role", ["member", "system_admin"])
def test_other_roles_cannot_register(
    client: TestClient,
    database_session: Session,
    role: str,
) -> None:
    with database_session.begin():
        user = database_session.get(User, USER_ID)
        assert user is not None
        user.role = role
        if role == "system_admin":
            user.company_id = None

    response = client.post("/devices", json=PAYLOAD)

    assert response.status_code == 403
    assert_no_devices(database_session)


def test_inactive_company_cannot_register(
    client: TestClient,
    database_session: Session,
) -> None:
    with database_session.begin():
        company = database_session.get(Company, COMPANY_ID)
        assert company is not None
        company.status = "inactive"

    response = client.post("/devices", json=PAYLOAD)

    assert response.status_code == 403
    assert_no_devices(database_session)


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " \t "},
        {"name": "x" * 101},
        {"description": "x" * 1001},
        {"device_type": "unsupported"},
        {"company_id": str(OTHER_COMPANY_ID)},
        {"status": "inactive"},
    ],
)
def test_invalid_input_does_not_create_device(
    client: TestClient,
    database_session: Session,
    changes: dict[str, object],
) -> None:
    response = client.post("/devices", json={**PAYLOAD, **changes})

    assert response.status_code == 422
    assert_no_devices(database_session)


def test_duplicate_names_and_supplied_description_are_preserved(
    client: TestClient, database_session: Session
) -> None:
    payload = {**PAYLOAD, "description": "Main warehouse freezer"}
    first = client.post("/devices", json=payload)
    second = client.post("/devices", json=payload)
    assert first.status_code == second.status_code == 201
    ids = {UUID(first.json()["id"]), UUID(second.json()["id"])}
    assert len(ids) == 2
    assert first.json()["description"] == payload["description"]
    assert second.json()["description"] == payload["description"]
    with database_session.begin():
        devices = database_session.scalars(
            select(Device).where(Device.id.in_(ids))
        ).all()
        assert len(devices) == 2
        assert all(device.name == "Freezer sensor 01" for device in devices)
        assert all(device.description == payload["description"] for device in devices)


def test_authentication_is_required(
    client: TestClient,
    database_session: Session,
) -> None:
    client.headers.pop("Authorization")
    response = client.post("/devices", json=PAYLOAD)

    assert response.status_code == 401
    assert_no_devices(database_session)


@pytest.mark.parametrize("phase", ["after_insert", "before_commit"])
@pytest.mark.parametrize("failure", ["connection", "timeout"])
def test_registration_failure_rolls_back(
    client: TestClient,
    database_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    failure: str,
) -> None:
    original_insert = application.insert_device

    def raise_failure() -> None:
        if failure == "connection":
            raise OperationalError(
                "private SQL",
                {},
                Exception("private database details"),
            )
        raise SQLAlchemyTimeoutError("private database details")

    def fail_before_commit(session: Session) -> None:
        raise_failure()

    def insert_then_fail(
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

        if phase == "after_insert":
            raise_failure()

        event.listen(session, "before_commit", fail_before_commit, once=True)
        return device

    try:
        with monkeypatch.context() as patch:
            patch.setattr(application, "insert_device", insert_then_fail)
            response = client.post("/devices", json=PAYLOAD)
    finally:
        if event.contains(database_session, "before_commit", fail_before_commit):
            event.remove(database_session, "before_commit", fail_before_commit)

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "Device registration temporarily unavailable."}
    assert_no_devices(database_session)

    recovery = client.post("/devices", json=PAYLOAD)
    assert recovery.status_code == 201

    with database_session.begin():
        device_ids = database_session.scalars(
            select(Device.id).where(Device.company_id == COMPANY_ID)
        ).all()
        assert device_ids == [UUID(recovery.json()["id"])]
