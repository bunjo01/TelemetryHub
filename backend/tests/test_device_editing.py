from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event
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
SECRET = "device-editing-test-secret-" * 3
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
                Company(id=COMPANY_ID, name="Editing test company"),
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


@pytest.mark.parametrize(
    ("payload", "name", "description"),
    [
        ({"name": "  New name  "}, "New name", "Warehouse freezer"),
        ({"description": "New description"}, "Freezer sensor", "New description"),
        ({"description": None}, "Freezer sensor", None),
        ({"description": ""}, "Freezer sensor", ""),
        ({"name": "New", "description": "Both"}, "New", "Both"),
        ({"name": "x" * 100, "description": "y" * 1000}, "x" * 100, "y" * 1000),
    ],
)
def test_owner_edits_only_requested_fields(
    client: TestClient,
    database_session: Session,
    payload: dict[str, str | None],
    name: str,
    description: str | None,
) -> None:
    with database_session.begin():
        device = database_session.get(Device, DEVICE_ID)
        assert device is not None
        device.updated_at = BASE_TIME
    before = client.get(f"/devices/{DEVICE_ID}").json()
    response = client.patch(f"/devices/{DEVICE_ID}", json=payload)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body == {
        **before,
        "name": name,
        "description": description,
        "updated_at": body["updated_at"],
    }
    assert datetime.fromisoformat(body["updated_at"]) > BASE_TIME
    with database_session.begin():
        database_session.expire_all()
        stored = database_session.get(Device, DEVICE_ID)
        assert stored is not None
        assert stored.name == name
        assert stored.description == description
        assert stored.status == "active"
        assert stored.updated_at == datetime.fromisoformat(body["updated_at"])


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Freezer sensor"},
        {"name": "  Freezer sensor  "},
        {"description": "Warehouse freezer"},
        {"name": "Freezer sensor", "description": "Warehouse freezer"},
    ],
)
def test_unchanged_edit_preserves_timestamp(
    client: TestClient, payload: dict[str, str]
) -> None:
    before = client.get(f"/devices/{DEVICE_ID}").json()
    response = client.patch(f"/devices/{DEVICE_ID}", json=payload)
    assert response.status_code == 200
    assert response.json() == before
    assert client.get(f"/devices/{DEVICE_ID}").json() == before


def test_clearing_already_null_description_preserves_timestamp(
    client: TestClient, database_session: Session
) -> None:
    with database_session.begin():
        device = database_session.get(Device, DEVICE_ID)
        assert device is not None
        device.description = None
        device.updated_at = BASE_TIME
    before = client.get(f"/devices/{DEVICE_ID}").json()
    response = client.patch(f"/devices/{DEVICE_ID}", json={"description": None})
    assert response.status_code == 200
    assert response.json() == before


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": None},
        {"name": " \t "},
        {"name": ""},
        {"name": "x" * 101},
        {"name": 123},
        {"description": "x" * 1001},
        {"description": 123},
        {"status": "inactive"},
        {"device_type": "gps_tracker"},
        {"company_id": str(OTHER_COMPANY_ID)},
        {"id": str(uuid4())},
        {"created_at": "2020-01-01T00:00:00Z"},
        {"updated_at": "2020-01-01T00:00:00Z"},
        {"name": "Valid", "unknown": True},
    ],
)
def test_invalid_edit_does_not_change_device(
    client: TestClient, payload: dict[str, object]
) -> None:
    before = client.get(f"/devices/{DEVICE_ID}").json()
    response = client.patch(f"/devices/{DEVICE_ID}", json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data."}
    assert response.headers["cache-control"] == "no-store"
    assert client.get(f"/devices/{DEVICE_ID}").json() == before


@pytest.mark.parametrize("target", ["missing", "other_company"])
def test_missing_and_other_company_devices_return_same_error(
    client: TestClient, database_session: Session, target: str
) -> None:
    target_id = uuid4() if target == "missing" else OTHER_DEVICE_ID
    response = client.patch(f"/devices/{target_id}", json={"name": "Forbidden"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Device not found."}
    assert response.headers["cache-control"] == "no-store"
    with database_session.begin():
        other = database_session.get(Device, OTHER_DEVICE_ID)
        assert other is not None
        assert other.name == "Other company's sensor"


@pytest.mark.parametrize("denial", ["member", "system_admin", "inactive_company"])
def test_edit_permissions(
    client: TestClient, database_session: Session, denial: str
) -> None:
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
    response = client.patch(f"/devices/{DEVICE_ID}", json={"name": "Forbidden"})
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    with database_session.begin():
        device = database_session.get(Device, DEVICE_ID)
        assert device is not None
        assert device.name == "Freezer sensor"
        assert device.updated_at == BASE_TIME


@pytest.mark.parametrize("credentials", ["missing", "invalid", "inactive_user"])
def test_authentication_required(
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
    response = client.patch(f"/devices/{DEVICE_ID}", json={"name": "Forbidden"})
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    with database_session.begin():
        device = database_session.get(Device, DEVICE_ID)
        assert device is not None
        assert device.name == "Freezer sensor"


def test_inactive_device_can_be_renamed_to_existing_name(
    client: TestClient, database_session: Session
) -> None:
    sibling_id = uuid4()
    with database_session.begin():
        device = database_session.get(Device, DEVICE_ID)
        assert device is not None
        device.status = "inactive"
        database_session.add(
            Device(
                id=sibling_id,
                company_id=COMPANY_ID,
                name="Shared name",
                description="Sibling",
                device_type="gps_tracker",
            )
        )
    response = client.patch(
        f"/devices/{DEVICE_ID}", json={"name": "Shared name", "description": None}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    with database_session.begin():
        database_session.expire_all()
        edited = database_session.get(Device, DEVICE_ID)
        sibling = database_session.get(Device, sibling_id)
        assert edited is not None and sibling is not None
        assert edited.name == sibling.name == "Shared name"
        assert edited.description is None
        assert edited.status == "inactive"
        assert sibling.description == "Sibling"


def test_invalid_device_id(client: TestClient) -> None:
    response = client.patch("/devices/not-a-uuid", json={"name": "New"})
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data."}


@pytest.mark.parametrize("phase", ["after_update", "before_commit"])
@pytest.mark.parametrize("failure", ["connection", "timeout"])
def test_failed_edit_rolls_back_and_session_recovers(
    client: TestClient,
    database_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    failure: str,
) -> None:
    original_update = application.update_device_details
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
        if phase == "after_update":
            raise_failure()
        event.listen(session, "before_commit", fail_before_commit, once=True)
        return device

    try:
        with monkeypatch.context() as patch:
            patch.setattr(application, "update_device_details", update_then_fail)
            response = client.patch(
                f"/devices/{DEVICE_ID}", json={"name": "New", "description": None}
            )
    finally:
        if event.contains(database_session, "before_commit", fail_before_commit):
            event.remove(database_session, "before_commit", fail_before_commit)
    assert response.status_code == 503
    assert response.json() == {"detail": "Device editing temporarily unavailable."}
    assert response.headers["cache-control"] == "no-store"
    assert client.get(f"/devices/{DEVICE_ID}").json() == before
    recovery = client.patch(f"/devices/{DEVICE_ID}", json={"name": "Recovered"})
    assert recovery.status_code == 200
    assert recovery.json()["name"] == "Recovered"
