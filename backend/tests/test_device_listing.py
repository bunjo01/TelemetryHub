from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import delete
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
from app.infrastructure.repositories.devices import DevicePage
from app.infrastructure.tokens import create_access_token
from app.main import handle_request_validation_error

SECRET = "device-listing-test-secret-" * 3
COMPANY_ID = uuid4()
OTHER_COMPANY_ID = uuid4()
USER_ID = uuid4()
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
# Explicit IDs and timestamps make the tie-breaking order reproducible.
DEVICE_IDS = [UUID(int=index) for index in range(1, 7)]
ACTIVE_IDS = [DEVICE_IDS[index] for index in (3, 2, 1, 0)]
ALL_IDS = [DEVICE_IDS[4], *ACTIVE_IDS]


@pytest.fixture
def client(database_session: Session) -> Iterator[TestClient]:
    with database_session.begin():
        database_session.add_all(
            [
                Company(id=COMPANY_ID, name="Listing company"),
                Company(id=OTHER_COMPANY_ID, name="Other listing company"),
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
        for index, name in enumerate(
            [
                "Freezer sensor",
                "Humidity 50%",
                "Room_A",
                "Room/A",
                "Freezer retired",
                "Freezer other company",
            ]
        ):
            database_session.add(
                Device(
                    id=DEVICE_IDS[index],
                    company_id=OTHER_COMPANY_ID if index == 5 else COMPANY_ID,
                    name=name,
                    description="Description-only keyword",
                    device_type="temperature_sensor",
                    status="inactive" if index == 4 else "active",
                    created_at=CREATED_AT + timedelta(days=index // 2),
                    updated_at=CREATED_AT,
                )
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
@pytest.mark.parametrize("device_status", [None, "active", "inactive", "all"])
def test_listing_filters_status_and_company(
    client: TestClient,
    database_session: Session,
    role: str,
    device_status: str | None,
) -> None:
    with database_session.begin():
        user = database_session.get(User, USER_ID)
        assert user is not None
        user.role = role

    params = {} if device_status is None else {"status": device_status}
    response = client.get("/devices", params=params)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    expected = (
        ALL_IDS
        if device_status == "all"
        else [DEVICE_IDS[4]]
        if device_status == "inactive"
        else ACTIVE_IDS
    )
    assert [item["id"] for item in body["items"]] == [str(id_) for id_ in expected]
    assert all(item["company_id"] == str(COMPANY_ID) for item in body["items"])
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["has_more"] is False
    item = body["items"][0]
    details = client.get(f"/devices/{item['id']}")
    assert details.status_code == 200
    assert item == details.json()


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("  fReEzEr  ", [DEVICE_IDS[4], DEVICE_IDS[0]]),
        ("reez", [DEVICE_IDS[4], DEVICE_IDS[0]]),
        ("%", [DEVICE_IDS[1]]),
        ("_", [DEVICE_IDS[2]]),
        ("/", [DEVICE_IDS[3]]),
        ("", ALL_IDS),
        (" \t ", ALL_IDS),
        ("Description-only", []),
        ("no match", []),
        ("x" * 100, []),
        ("' OR 1=1 --", []),
    ],
)
def test_search_is_trimmed_case_insensitive_and_literal(
    client: TestClient, search: str, expected: list[UUID]
) -> None:
    response = client.get("/devices", params={"status": "all", "search": search})
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [str(id_) for id_ in expected]
    assert body["has_more"] is False


def test_search_and_status_apply_before_pagination(client: TestClient) -> None:
    response = client.get(
        "/devices", params={"search": "freezer", "limit": 1, "offset": 0}
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(DEVICE_IDS[0])]
    assert response.json()["has_more"] is False


@pytest.mark.parametrize(
    ("limit", "offset", "expected", "has_more"),
    [
        (2, 0, ACTIVE_IDS[:2], True),
        (2, 2, ACTIVE_IDS[2:], False),
        (3, 3, ACTIVE_IDS[3:], False),
        (2, 4, [], False),
        (2, 100, [], False),
        (1, 0, ACTIVE_IDS[:1], True),
        (100, 0, ACTIVE_IDS, False),
    ],
)
def test_pagination_boundaries(
    client: TestClient, limit: int, offset: int, expected: list[UUID], has_more: bool
) -> None:
    response = client.get("/devices", params={"limit": limit, "offset": offset})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "limit", "offset", "has_more"}
    assert [item["id"] for item in body["items"]] == [str(id_) for id_ in expected]
    assert body["limit"] == limit
    assert body["offset"] == offset
    assert body["has_more"] is has_more


def test_company_with_no_devices_gets_empty_page(
    client: TestClient, database_session: Session
) -> None:
    with database_session.begin():
        database_session.execute(delete(Device).where(Device.company_id == COMPANY_ID))
    response = client.get("/devices")
    assert response.status_code == 200
    assert response.json() == {"items": [], "limit": 20, "offset": 0, "has_more": False}


@pytest.mark.parametrize(
    "params",
    [
        {"status": "unsupported"},
        {"limit": "0"},
        {"limit": "101"},
        {"limit": "1.5"},
        {"limit": "abc"},
        {"offset": "-1"},
        {"offset": "1.5"},
        {"offset": "abc"},
        {"search": "x" * 101},
        {"company_id": str(OTHER_COMPANY_ID)},
        {"unknown": "value"},
    ],
)
def test_invalid_query_is_rejected(client: TestClient, params: dict[str, str]) -> None:
    response = client.get("/devices", params=params)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data."}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("role", ["company_owner", "member"])
def test_inactive_company_cannot_list(
    client: TestClient, database_session: Session, role: str
) -> None:
    with database_session.begin():
        user = database_session.get(User, USER_ID)
        company = database_session.get(Company, COMPANY_ID)
        assert user is not None and company is not None
        user.role = role
        company.status = "inactive"
    response = client.get("/devices")
    assert response.status_code == 403
    assert response.json() == {"detail": "Company is unavailable."}
    assert response.headers["cache-control"] == "no-store"


def test_system_admin_cannot_list(
    client: TestClient, database_session: Session
) -> None:
    with database_session.begin():
        user = database_session.get(User, USER_ID)
        assert user is not None
        user.role = "system_admin"
        user.company_id = None
    response = client.get("/devices")
    assert response.status_code == 403
    assert response.json() == {"detail": "Company owner or member access required."}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("credentials", ["missing", "invalid", "inactive_user"])
def test_unavailable_credentials_cannot_list(
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
    response = client.get("/devices")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("failure", ["connection", "timeout"])
def test_listing_failure_is_sanitized_and_session_recovers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    def fail_lookup(
        session: Session,
        *,
        company_id: UUID,
        device_status: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> DevicePage:
        if failure == "connection":
            raise OperationalError("private SQL", {}, Exception("private details"))
        raise SQLAlchemyTimeoutError("private details")

    with monkeypatch.context() as patch:
        patch.setattr(application, "read_device_page", fail_lookup)
        response = client.get("/devices")
    assert response.status_code == 503
    assert response.json() == {"detail": "Device listing temporarily unavailable."}
    assert response.headers["cache-control"] == "no-store"
    recovery = client.get("/devices")
    assert recovery.status_code == 200
    assert len(recovery.json()["items"]) == 4
