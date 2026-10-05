import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api import dependencies
from app.api import invitations as api
from app.application.invitations import (
    CompanyNotFoundError,
    CreatedOwnerInvitation,
    InvitationConflictError,
    create_owner_invitation,
)
from app.config import Settings
from app.infrastructure.models.company import Company
from app.infrastructure.models.invitation import Invitation
from app.infrastructure.models.user import User
from app.infrastructure.repositories.users import CurrentUser
from app.main import app as main_app
from app.main import handle_request_validation_error

ADMIN_ID = uuid4()
COMPANY_ID = uuid4()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(api.router)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.dependency_overrides[dependencies.get_settings] = lambda: (
        Settings.model_construct()
    )
    app.dependency_overrides[dependencies.get_database_session] = lambda: None
    app.dependency_overrides[dependencies.get_current_user] = lambda: CurrentUser(
        ADMIN_ID, None, "admin@example.com", "system_admin", "active"
    )

    def unexpected_create(**kwargs):
        pytest.fail("Rejected request reached invitation creation")

    monkeypatch.setattr(api, "create_owner_invitation", unexpected_create)
    with TestClient(app) as test_client:
        yield test_client


def test_create_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def create(**kwargs):
        assert kwargs["email"] == "owner@example.com"
        assert kwargs["company_id"] == COMPANY_ID
        assert kwargs["invited_by_id"] == ADMIN_ID
        assert kwargs["expires_in_hours"] == 24
        return CreatedOwnerInvitation(
            uuid4(), COMPANY_ID, kwargs["email"], datetime.now(UTC), "test-token"
        )

    monkeypatch.setattr(api, "create_owner_invitation", create)
    response = client.post(
        f"/companies/{COMPANY_ID}/owner-invitations",
        json={"email": " OWNER@example.com "},
    )
    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json()["token"] == "test-token"
    assert response.json()["role"] == "company_owner"
    assert "token_hash" not in response.json()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "invalid"},
        {"email": "a@example.com", "role": "member"},
        {"email": "a@example.com", "invited_by_id": str(ADMIN_ID)},
    ],
)
def test_invalid_payload(client: TestClient, payload: dict) -> None:
    assert (
        client.post(
            f"/companies/{COMPANY_ID}/owner-invitations", json=payload
        ).status_code
        == 422
    )


@pytest.mark.parametrize("role", ["member", "company_owner"])
def test_requires_admin(client: TestClient, role: str) -> None:
    client.app.dependency_overrides[dependencies.get_current_user] = lambda: (
        CurrentUser(ADMIN_ID, COMPANY_ID, "user@example.com", role, "active")
    )
    assert (
        client.post(
            f"/companies/{COMPANY_ID}/owner-invitations",
            json={"email": "a@example.com"},
        ).status_code
        == 403
    )


def test_requires_token(client: TestClient) -> None:
    del client.app.dependency_overrides[dependencies.get_current_user]
    assert (
        client.post(
            f"/companies/{COMPANY_ID}/owner-invitations",
            json={"email": "a@example.com"},
        ).status_code
        == 401
    )


def test_invalid_company_id(client: TestClient) -> None:
    response = client.post(
        "/companies/not-a-uuid/owner-invitations", json={"email": "owner@example.com"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("kind", ["connection", "timeout"])
def test_database_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    def fail(**kwargs):
        if kind == "connection":
            raise OperationalError("private SQL", {}, Exception("private details"))
        raise SQLAlchemyTimeoutError("private details")

    monkeypatch.setattr(api, "create_owner_invitation", fail)
    response = client.post(
        f"/companies/{COMPANY_ID}/owner-invitations", json={"email": "a@example.com"}
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Invitation creation temporarily unavailable."}


def test_router_registered() -> None:
    operation = main_app.openapi()["paths"][
        "/companies/{company_id}/owner-invitations"
    ]["post"]
    assert "201" in operation["responses"]
    assert operation["security"] == [{"HTTPBearer": []}]


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (CompanyNotFoundError(), 404),
        (InvitationConflictError("Conflict."), 409),
    ],
)
def test_business_errors(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status_code: int,
) -> None:
    def fail(**kwargs):
        raise error

    monkeypatch.setattr(api, "create_owner_invitation", fail)
    assert (
        client.post(
            f"/companies/{COMPANY_ID}/owner-invitations",
            json={"email": "a@example.com"},
        ).status_code
        == status_code
    )


def seed(session: Session) -> tuple:
    admin_id, company_id = uuid4(), uuid4()
    with session.begin():
        session.add(
            User(
                id=admin_id,
                email=f"{admin_id}@example.com",
                password_hash="test-placeholder",
                role="system_admin",
            )
        )
        session.add(Company(id=company_id, name="Invitation test"))
    return admin_id, company_id


def test_postgres_hash_expiry_and_pending_conflict(database_session: Session) -> None:
    session = database_session
    admin_id, company_id = seed(session)
    email = f"{uuid4()}@example.com"
    result = create_owner_invitation(session, company_id, admin_id, email, 24)
    with session.begin():
        row = session.get(Invitation, result.id)
        assert row.token_hash == hashlib.sha256(result.token.encode()).hexdigest()
        assert row.token_hash != result.token
        assert row.expires_at - row.created_at == timedelta(hours=24)
        assert row.invited_by_id == admin_id and row.role == "company_owner"
        assert row.accepted_at is None
    assert result.token not in repr(result)
    with pytest.raises(InvitationConflictError, match="pending"):
        create_owner_invitation(session, company_id, admin_id, email, 24)
    # Expired invitations do not prevent issuing a new invitation.
    with session.begin():
        row = session.get(Invitation, result.id)
        row.created_at = datetime.now(UTC) - timedelta(days=2)
        row.expires_at = datetime.now(UTC) - timedelta(days=1)
    replacement = create_owner_invitation(session, company_id, admin_id, email, 24)
    assert replacement.token != result.token


@pytest.mark.parametrize("scenario", ["missing", "inactive", "owner", "email"])
def test_postgres_rejects_conflicts(database_session: Session, scenario: str) -> None:
    session = database_session
    admin_id, company_id = seed(session)
    email = f"{uuid4()}@example.com"
    with session.begin():
        if scenario == "inactive":
            session.get(Company, company_id).status = "inactive"
        elif scenario in ("owner", "email"):
            session.add(
                User(
                    email=email,
                    password_hash="test-placeholder",
                    role="company_owner" if scenario == "owner" else "system_admin",
                    company_id=company_id if scenario == "owner" else None,
                )
            )
    target_id = uuid4() if scenario == "missing" else company_id
    expected = (
        CompanyNotFoundError if scenario == "missing" else InvitationConflictError
    )
    with pytest.raises(expected):
        create_owner_invitation(session, target_id, admin_id, email, 24)
    with session.begin():
        assert (
            session.scalar(
                select(Invitation.id).where(Invitation.company_id == company_id)
            )
            is None
        )
