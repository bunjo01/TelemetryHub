from collections.abc import Iterator
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import SecretStr
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

SECRET = "device-details-test-secret-" * 3
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
                Company(id=COMPANY_ID, name="Details test company"),
                Company(id=OTHER_COMPANY_ID, name="Other details company"),
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


@pytest.mark.parametrize("role", ["company_owner", "member"])
@pytest.mark.parametrize("device_status", ["active", "inactive"])
def test_company_users_can_read_device_details(
    client: TestClient,
    database_session: Session,
    role: str,
    device_status: str,
) -> None:
    with database_session.begin():
        user = database_session.get(User, USER_ID)
        device = database_session.get(Device, DEVICE_ID)
        assert user is not None and device is not None
        user.role = role
        device.status = device_status
        database_session.flush()
        created_at, updated_at = device.created_at, device.updated_at

    response = client.get(f"/devices/{DEVICE_ID}")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body == {
        "id": str(DEVICE_ID),
        "company_id": str(COMPANY_ID),
        "name": "Freezer sensor",
        "description": "Warehouse freezer",
        "device_type": "temperature_sensor",
        "status": device_status,
        "created_at": body["created_at"],
        "updated_at": body["updated_at"],
    }
    assert datetime.fromisoformat(body["created_at"]) == created_at
    assert datetime.fromisoformat(body["updated_at"]) == updated_at
    with database_session.begin():
        database_session.expire_all()
        stored = database_session.get(Device, DEVICE_ID)
        assert stored is not None
        assert stored.status == device_status
        assert stored.updated_at == updated_at


@pytest.mark.parametrize("role", ["company_owner", "member"])
def test_other_company_device_is_indistinguishable_from_missing_device(
    client: TestClient, database_session: Session, role: str
) -> None:
    with database_session.begin():
        user = database_session.get(User, USER_ID)
        assert user is not None
        user.role = role

    for device_id in (OTHER_DEVICE_ID, uuid4()):
        response = client.get(f"/devices/{device_id}")
        assert response.status_code == 404
        assert response.json() == {"detail": "Device not found."}
        assert response.headers["cache-control"] == "no-store"


def test_system_admin_cannot_read_devices(
    client: TestClient, database_session: Session
) -> None:
    with database_session.begin():
        user = database_session.get(User, USER_ID)
        assert user is not None
        user.role = "system_admin"
        user.company_id = None

    response = client.get(f"/devices/{DEVICE_ID}")
    assert response.status_code == 403
    assert response.json() == {"detail": "Company owner or member access required."}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("role", ["company_owner", "member"])
def test_inactive_company_cannot_read_devices(
    client: TestClient, database_session: Session, role: str
) -> None:
    with database_session.begin():
        user = database_session.get(User, USER_ID)
        company = database_session.get(Company, COMPANY_ID)
        assert user is not None and company is not None
        user.role = role
        company.status = "inactive"

    response = client.get(f"/devices/{DEVICE_ID}")
    assert response.status_code == 403
    assert response.json() == {"detail": "Company is unavailable."}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("credentials", ["missing", "invalid", "inactive_user"])
def test_unavailable_credentials_cannot_read_devices(
    client: TestClient, database_session: Session, credentials: str
) -> None:
    if credentials == "missing":
        client.headers.pop("Authorization")
    elif credentials == "invalid":
        client.headers["Authorization"] = "Bearer invalid-token"
    else:
        with database_session.begin():
            user = database_session.get(User, USER_ID)
            assert user is not None
            user.status = "inactive"

    response = client.get(f"/devices/{DEVICE_ID}")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


def test_invalid_device_id_is_rejected(client: TestClient) -> None:
    response = client.get("/devices/not-a-uuid")
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data."}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("failure", ["connection", "timeout"])
def test_device_lookup_failure_is_sanitized_and_session_recovers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    def fail_lookup(
        session: Session, *, company_id: UUID, device_id: UUID
    ) -> DeviceDetails | None:
        if failure == "connection":
            raise OperationalError("private SQL", {}, Exception("private details"))
        raise SQLAlchemyTimeoutError("private details")

    with monkeypatch.context() as patch:
        patch.setattr(application, "read_device_details", fail_lookup)
        response = client.get(f"/devices/{DEVICE_ID}")

    assert response.status_code == 503
    assert response.json() == {"detail": "Device details temporarily unavailable."}
    assert response.headers["cache-control"] == "no-store"
    assert client.get(f"/devices/{DEVICE_ID}").status_code == 200
