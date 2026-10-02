from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api import dependencies
from app.api.auth import router
from app.application import authentication
from app.config import Settings
from app.infrastructure.repositories.users import CurrentUser
from app.infrastructure.tokens import create_access_token

SECRET = "test-only-secret-" * 4
USER_ID = UUID("128a2f01-d049-43b8-98ca-afae7b78d907")
COMPANY_ID = UUID("28f63fb6-b64f-4607-bb79-a6e815ab9131")


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)

    # Avoid loading local environment secrets. Only this setting is used here.
    settings = Settings.model_construct(jwt_secret_key=SecretStr(SECRET))

    def get_session() -> Iterator[Session]:
        # Real transaction lifecycle, no database connection: replace the query
        # at the repository boundary in each test instead.
        with Session() as session:
            yield session

    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.get_database_session] = get_session
    with TestClient(app) as test_client:
        yield test_client


def authorization_header() -> dict[str, str]:
    token = create_access_token(USER_ID, SECRET, 15)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("role", "company_id"),
    [("system_admin", None), ("company_owner", COMPANY_ID), ("member", COMPANY_ID)],
)
def test_me_returns_public_user(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    company_id: UUID | None,
) -> None:
    def find_user(session: Session, user_id: UUID) -> CurrentUser:
        assert user_id == USER_ID
        return CurrentUser(user_id, company_id, "user@example.com", role, "active")

    monkeypatch.setattr(authentication, "find_user_by_id", find_user)
    response = client.get("/auth/me", headers=authorization_header())

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "id": str(USER_ID),
        "company_id": str(company_id) if company_id else None,
        "email": "user@example.com",
        "role": role,
        "status": "active",
    }


@pytest.mark.parametrize(
    "header",
    [None, "Basic abc", "Bearer", "Bearer invalid-token"],
)
def test_me_rejects_bad_credentials_before_querying(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, header: str | None
) -> None:
    def unexpected_query(session: Session, user_id: UUID) -> None:
        pytest.fail("Invalid credentials must not reach the repository")

    monkeypatch.setattr(authentication, "find_user_by_id", unexpected_query)
    headers = {} if header is None else {"Authorization": header}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {"detail": "Could not validate credentials."}


@pytest.mark.parametrize("user_status", [None, "inactive"])
def test_me_rejects_missing_or_inactive_users(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, user_status: str | None
) -> None:
    def find_user(session: Session, user_id: UUID) -> CurrentUser | None:
        if user_status is None:
            return None
        return CurrentUser(
            user_id, None, "user@example.com", "system_admin", user_status
        )

    monkeypatch.setattr(authentication, "find_user_by_id", find_user)
    response = client.get("/auth/me", headers=authorization_header())

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("failure_kind", ["connection", "pool_timeout"])
def test_me_hides_database_failures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, failure_kind: str
) -> None:
    def fail_query(session: Session, user_id: UUID) -> None:
        if failure_kind == "connection":
            raise OperationalError("private SQL", {}, Exception("private connection"))
        raise SQLAlchemyTimeoutError("private pool details")

    monkeypatch.setattr(authentication, "find_user_by_id", fail_query)
    response = client.get("/auth/me", headers=authorization_header())

    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {"detail": "Authentication temporarily unavailable."}
