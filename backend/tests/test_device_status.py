from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api import dependencies
from app.api.devices import router
from app.application import devices as application
from app.config import Settings
from app.infrastructure.models.company import Company
from app.infrastructure.models.device import Device
from app.infrastructure.models.user import User
from app.infrastructure.repositories.devices import DeviceDetails
from app.infrastructure.tokens import create_access_token
from app.main import handle_request_validation_error

BASE_TIME = datetime(2020, 1, 1, tzinfo=UTC)
SECRET = "device-status-test-secret-" * 3
COMPANY_ID = uuid4()
OTHER_COMPANY_ID = uuid4()
USER_ID = uuid4()
DEVICE_ID = uuid4()
OTHER_DEVICE_ID = uuid4()


@pytest.fixture
def client(database_session: Session) -> Iterator[TestClient]:
    with database_session.begin():
        database_session.add_all(
            [
                Company(id=COMPANY_ID, name="Status test company"),
                Company(id=OTHER_COMPANY_ID, name="Other editing company"),
            ]
        )
        database_session.flush()
        database_session.add_all(
            [
                User(
                    id=USER_ID,
                    company_id=COMPANY_ID,
                    email=f"{USER_ID}@example.com",
                    password_hash="test-only",
                    role="company_owner",
                ),
                Device(
                    id=DEVICE_ID,
                    company_id=COMPANY_ID,
                    name="Freezer sensor",
                    description="Warehouse freezer",
                    device_type="temperature_sensor",
                    created_at=BASE_TIME,
                    updated_at=BASE_TIME,
                ),
                Device(
                    id=OTHER_DEVICE_ID,
                    company_id=OTHER_COMPANY_ID,
                    name="Other company's sensor",
                    device_type="gps_tracker",
                ),
            ]
        )

    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    settings = Settings.model_construct(jwt_secret_key=SecretStr(SECRET))

    def get_session() -> Iterator[Session]:
        yield database_session

    app.dependency_overrides[dependencies.get_database_session] = get_session
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    token = create_access_token(USER_ID, SECRET, 15)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client


@pytest.fixture(
    params=[("activate", "inactive", "active"), ("deactivate", "active", "inactive")]
)
def transition(
    request: pytest.FixtureRequest,
    client: TestClient,
    database_session: Session,
) -> tuple[str, str, str]:
    action, initial, target = request.param
    with database_session.begin():
        # Explicit values prevent onupdate from replacing the baseline timestamp.
        database_session.execute(
            update(Device)
            .where(Device.id.in_((DEVICE_ID, OTHER_DEVICE_ID)))
            .values(status=initial, updated_at=BASE_TIME)
        )
    return action, initial, target


def test_owner_changes_status_and_repeated_request_is_unchanged(
    client: TestClient,
    database_session: Session,
    transition: tuple[str, str, str],
) -> None:
    action, initial, target = transition
    before = client.get(f"/devices/{DEVICE_ID}").json()
    response = client.post(f"/devices/{DEVICE_ID}/{action}")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body == {**before, "status": target, "updated_at": body["updated_at"]}
    assert datetime.fromisoformat(body["updated_at"]) > BASE_TIME
    repeated = client.post(f"/devices/{DEVICE_ID}/{action}")
    assert repeated.status_code == 200
    assert repeated.json() == body
    assert client.get(f"/devices/{DEVICE_ID}").json() == body
    with database_session.begin():
        database_session.expire_all()
        stored = database_session.get(Device, DEVICE_ID)
        other = database_session.get(Device, OTHER_DEVICE_ID)
        assert stored is not None and other is not None
        assert stored.status == target
        assert stored.updated_at == datetime.fromisoformat(body["updated_at"])
        assert other.status == initial
        assert other.updated_at == BASE_TIME

    matching = client.get("/devices", params={"status": target}).json()
    old_status = client.get("/devices", params={"status": initial}).json()
    assert [item["id"] for item in matching["items"]] == [str(DEVICE_ID)]
    assert old_status["items"] == []
    edited = client.patch(f"/devices/{DEVICE_ID}", json={"name": "Still editable"})
    assert edited.status_code == 200
    assert edited.json()["name"] == "Still editable"
    assert edited.json()["status"] == target


def test_already_requested_status_preserves_old_timestamp(
    client: TestClient,
    database_session: Session,
    transition: tuple[str, str, str],
) -> None:
    action, _, target = transition
    with database_session.begin():
        database_session.execute(
            update(Device)
            .where(Device.id == DEVICE_ID)
            .values(status=target, updated_at=BASE_TIME)
        )
    before = client.get(f"/devices/{DEVICE_ID}").json()
    assert datetime.fromisoformat(before["updated_at"]) == BASE_TIME
    response = client.post(f"/devices/{DEVICE_ID}/{action}")
    assert response.status_code == 200
    assert response.json() == before
    with database_session.begin():
        database_session.expire_all()
        stored = database_session.get(Device, DEVICE_ID)
        assert stored is not None
        assert stored.status == target
        assert stored.updated_at == BASE_TIME


@pytest.mark.parametrize("target_device", ["missing", "other_company"])
def test_missing_and_foreign_devices_return_same_error(
    client: TestClient,
    database_session: Session,
    transition: tuple[str, str, str],
    target_device: str,
) -> None:
    action, initial, _ = transition
    target_id = uuid4() if target_device == "missing" else OTHER_DEVICE_ID
    response = client.post(f"/devices/{target_id}/{action}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Device not found."}
    assert response.headers["cache-control"] == "no-store"
    with database_session.begin():
        database_session.expire_all()
        for device_id in (DEVICE_ID, OTHER_DEVICE_ID):
            device = database_session.get(Device, device_id)
            assert device is not None
            assert device.status == initial
            assert device.updated_at == BASE_TIME


@pytest.mark.parametrize("denial", ["member", "system_admin", "inactive_company"])
def test_status_change_permissions(
    client: TestClient,
    database_session: Session,
    transition: tuple[str, str, str],
    denial: str,
) -> None:
    action, initial, _ = transition
    with database_session.begin():
        user = database_session.get(User, USER_ID)
        assert user is not None
        if denial == "inactive_company":
            company = database_session.get(Company, COMPANY_ID)
            assert company is not None
            company.status = "inactive"
        else:
            user.role = denial
            if denial == "system_admin":
                user.company_id = None
    response = client.post(f"/devices/{DEVICE_ID}/{action}")
    assert response.status_code == 403
    assert response.json() == {
        "detail": (
            "Company is unavailable."
            if denial == "inactive_company"
            else "Company owner access required."
        )
    }
    assert response.headers["cache-control"] == "no-store"
    with database_session.begin():
        database_session.expire_all()
        device = database_session.get(Device, DEVICE_ID)
        assert device is not None
        assert device.status == initial
        assert device.updated_at == BASE_TIME


@pytest.mark.parametrize("credentials", ["missing", "invalid", "inactive_user"])
def test_status_change_requires_authentication(
    client: TestClient,
    database_session: Session,
    transition: tuple[str, str, str],
    credentials: str,
) -> None:
    action, initial, _ = transition
    if credentials == "missing":
        client.headers.pop("Authorization")
    elif credentials == "invalid":
        client.headers["Authorization"] = "Bearer invalid-token"
    else:
        with database_session.begin():
            user = database_session.get(User, USER_ID)
            assert user is not None
            user.status = "inactive"
    response = client.post(f"/devices/{DEVICE_ID}/{action}")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    with database_session.begin():
        database_session.expire_all()
        device = database_session.get(Device, DEVICE_ID)
        assert device is not None
        assert device.status == initial
        assert device.updated_at == BASE_TIME


def test_invalid_device_id(
    client: TestClient, transition: tuple[str, str, str]
) -> None:
    action, _, _ = transition
    response = client.post(f"/devices/not-a-uuid/{action}")
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data."}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("phase", ["after_update", "before_commit"])
@pytest.mark.parametrize("failure", ["connection", "timeout"])
def test_failed_status_change_rolls_back_and_session_recovers(
    client: TestClient,
    database_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    transition: tuple[str, str, str],
    phase: str,
    failure: str,
) -> None:
    action, _, target = transition
    original_update = application.update_device_status
    before = client.get(f"/devices/{DEVICE_ID}").json()

    def raise_failure() -> None:
        if failure == "connection":
            raise OperationalError("private SQL", {}, Exception("private details"))
        raise SQLAlchemyTimeoutError("private details")

    def fail_before_commit(session: Session) -> None:
        raise_failure()

    def update_then_fail(
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
        if phase == "after_update":
            raise_failure()
        event.listen(session, "before_commit", fail_before_commit, once=True)
        return device

    try:
        with monkeypatch.context() as patch:
            patch.setattr(application, "update_device_status", update_then_fail)
            response = client.post(f"/devices/{DEVICE_ID}/{action}")
    finally:
        if event.contains(database_session, "before_commit", fail_before_commit):
            event.remove(database_session, "before_commit", fail_before_commit)
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Device status change temporarily unavailable."
    }
    assert response.headers["cache-control"] == "no-store"
    assert client.get(f"/devices/{DEVICE_ID}").json() == before
    recovery = client.post(f"/devices/{DEVICE_ID}/{action}")
    assert recovery.status_code == 200
    assert recovery.json()["status"] == target
