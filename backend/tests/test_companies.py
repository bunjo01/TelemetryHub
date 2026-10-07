from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api import dependencies
from app.api.companies import router
from app.application import authentication, companies
from app.config import Settings
from app.infrastructure.repositories.companies import CurrentCompany
from app.infrastructure.repositories.users import CurrentUser
from app.infrastructure.tokens import create_access_token
from app.main import app as main_app
from app.main import handle_request_validation_error

SECRET = "test-only-secret-" * 4
USER_ID = UUID("128a2f01-d049-43b8-98ca-afae7b78d907")
COMPANY_ID = UUID("28f63fb6-b64f-4607-bb79-a6e815ab9131")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    settings = Settings.model_construct(jwt_secret_key=SecretStr(SECRET))

    def get_session() -> Iterator[Session]:
        with Session() as session:
            yield session

    def find_admin(session: Session, user_id: UUID) -> CurrentUser:
        return CurrentUser(user_id, None, "admin@example.com", "system_admin", "active")

    def unexpected_insert(session: Session, name: str) -> CurrentCompany:
        pytest.fail("Rejected requests must not insert a company")

    monkeypatch.setattr(authentication, "find_user_by_id", find_admin)
    monkeypatch.setattr(companies, "insert_company", unexpected_insert)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.get_database_session] = get_session
    with TestClient(app) as test_client:
        yield test_client


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(USER_ID, SECRET, 15)}"}


@pytest.mark.parametrize("name", ["  IoT  ACME  ", "x" * 200, "  " + "x" * 200])
def test_admin_creates_company(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    def insert(session: Session, name: str) -> CurrentCompany:
        assert session.in_transaction()
        return CurrentCompany(COMPANY_ID, name, "active", NOW, NOW)

    monkeypatch.setattr(companies, "insert_company", insert)
    response = client.post("/companies", json={"name": name}, headers=headers())
    assert response.status_code == 201
    assert response.json() == {
        "id": str(COMPANY_ID),
        "name": name.strip(),
        "status": "active",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": ""},
        {"name": " \t "},
        {"name": "x" * 201},
        {"name": 123},
        {"name": None},
        {"name": "Acme", "status": "inactive"},
    ],
)
def test_invalid_input(client: TestClient, payload: dict[str, object]) -> None:
    response = client.post("/companies", json=payload, headers=headers())
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data."}


@pytest.mark.parametrize("role", ["member", "company_owner"])
def test_non_admin_is_forbidden(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    def find_user(session: Session, user_id: UUID) -> CurrentUser:
        return CurrentUser(user_id, COMPANY_ID, "user@example.com", role, "active")

    monkeypatch.setattr(authentication, "find_user_by_id", find_user)
    response = client.post("/companies", json={"name": "Acme"}, headers=headers())
    assert response.status_code == 403


@pytest.mark.parametrize("authorization", [None, "Bearer invalid", "Basic abc"])
def test_unauthenticated_request(client: TestClient, authorization: str | None) -> None:
    response = client.post(
        "/companies",
        json={"name": "Acme"},
        headers={"Authorization": authorization} if authorization else {},
    )
    assert response.status_code == 401


def test_inactive_admin(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def find_user(session: Session, user_id: UUID) -> CurrentUser:
        return CurrentUser(
            user_id, None, "admin@example.com", "system_admin", "inactive"
        )

    monkeypatch.setattr(authentication, "find_user_by_id", find_user)
    assert (
        client.post("/companies", json={"name": "Acme"}, headers=headers()).status_code
        == 401
    )


@pytest.mark.parametrize("phase", ["insert", "commit"])
@pytest.mark.parametrize("kind", ["connection", "timeout"])
def test_database_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, phase: str, kind: str
) -> None:
    def fail() -> None:
        if kind == "connection":
            raise OperationalError("private SQL", {}, Exception("private details"))
        raise SQLAlchemyTimeoutError("private details")

    def insert(session: Session, name: str) -> CurrentCompany:
        if phase == "insert":
            fail()
        else:
            from sqlalchemy import event

            event.listen(session, "before_commit", lambda session: fail(), once=True)
        return CurrentCompany(COMPANY_ID, name, "active", NOW, NOW)

    monkeypatch.setattr(companies, "insert_company", insert)
    response = client.post("/companies", json={"name": "Acme"}, headers=headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Company creation temporarily unavailable."}


def test_company_router_is_registered() -> None:
    operation = main_app.openapi()["paths"]["/companies"]["post"]
    assert "201" in operation["responses"]
    assert operation["security"] == [{"HTTPBearer": []}]


def test_admin_searches_companies(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.infrastructure.repositories.companies import CompanyOption

    def search(
        session: Session, query: str, limit: int, offset: int
    ) -> list[CompanyOption]:
        assert session.in_transaction()
        assert (query, limit, offset) == ("Orbital", 2, 0)
        return [
            CompanyOption(COMPANY_ID, "Orbital Labs"),
            CompanyOption(USER_ID, "Orbital Tools"),
        ]

    monkeypatch.setattr(companies, "search_companies", search)
    response = client.get("/companies?q=%20Orbital%20&limit=1", headers=headers())
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "items": [{"id": str(COMPANY_ID), "name": "Orbital Labs"}],
        "has_more": True,
    }


@pytest.mark.parametrize("role", ["member", "company_owner"])
def test_company_search_rejects_non_admin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    monkeypatch.setattr(
        authentication,
        "find_user_by_id",
        lambda session, user_id: CurrentUser(
            user_id, COMPANY_ID, "user@example.com", role, "active"
        ),
    )
    assert client.get("/companies", headers=headers()).status_code == 403


def test_company_search_requires_authentication(client: TestClient) -> None:
    assert client.get("/companies").status_code == 401


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=51", "offset=-1", "offset=10001", "q=" + "a" * 201]
)
def test_company_search_bounds(client: TestClient, query: str) -> None:
    assert client.get("/companies?" + query, headers=headers()).status_code == 422


def test_company_search_outage(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object) -> None:
        raise SQLAlchemyTimeoutError("private SQL")

    monkeypatch.setattr(companies, "search_companies", fail)
    response = client.get("/companies", headers=headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Company search temporarily unavailable."}


def test_company_search_in_postgres(database_session: Session) -> None:
    from uuid import uuid4

    from app.infrastructure.models.company import Company
    from app.infrastructure.repositories.companies import search_companies

    prefix = str(uuid4())
    database_session.add_all(
        [
            Company(name=f"{prefix} Beta"),
            Company(name=f"{prefix} Alpha"),
            Company(name=f"{prefix} Hidden", status="inactive"),
            Company(name=f"{prefix} 100%"),
        ]
    )
    database_session.flush()
    first = search_companies(database_session, prefix.upper(), 2, 0)
    second = search_companies(database_session, prefix, 2, 2)
    assert [item.name for item in first + second] == [
        f"{prefix} 100%",
        f"{prefix} Alpha",
        f"{prefix} Beta",
    ]
    assert [
        item.name
        for item in search_companies(database_session, f"{prefix} 100%", 20, 0)
    ] == [f"{prefix} 100%"]
    assert search_companies(database_session, f"{prefix}_", 20, 0) == []
