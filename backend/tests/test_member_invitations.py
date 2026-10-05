from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import dependencies
from app.api import invitations as api
from app.application import invitations as application
from app.config import Settings
from app.infrastructure.models.company import Company
from app.infrastructure.models.invitation import Invitation
from app.infrastructure.models.user import User
from app.infrastructure.passwords import verify_password
from app.infrastructure.repositories.users import CurrentUser
from app.main import handle_request_validation_error

COMPANY_ID = uuid4()
OWNER_ID = uuid4()
OWNER = CurrentUser(
    OWNER_ID, COMPANY_ID, "owner@example.com", "company_owner", "active"
)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(api.router)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.dependency_overrides[dependencies.get_current_user] = lambda: OWNER
    app.dependency_overrides[dependencies.get_settings] = lambda: (
        Settings.model_construct()
    )

    def session() -> Iterator[Session]:
        with Session() as value:
            yield value

    app.dependency_overrides[dependencies.get_database_session] = session

    def unexpected_query(*args):
        pytest.fail("Unauthorized request must not query company data")

    monkeypatch.setattr(application.repository, "lock_company_status", unexpected_query)
    with TestClient(app) as result:
        yield result


@pytest.mark.parametrize("role", ["member", "system_admin", "company_owner"])
def test_permission_and_company_isolation(client: TestClient, role: str) -> None:
    company_id = uuid4() if role == "company_owner" else COMPANY_ID
    client.app.dependency_overrides[dependencies.get_current_user] = lambda: (
        CurrentUser(OWNER_ID, COMPANY_ID, "user@example.com", role, "active")
    )
    response = client.post(
        f"/companies/{company_id}/member-invitations", json={"email": "a@example.com"}
    )
    assert response.status_code == 403


def test_no_token(client: TestClient) -> None:
    del client.app.dependency_overrides[dependencies.get_current_user]
    assert (
        client.post(
            f"/companies/{COMPANY_ID}/member-invitations",
            json={"email": "a@example.com"},
        ).status_code
        == 401
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "invalid"},
        {"email": "a@example.com", "role": "company_owner"},
        {"email": "a@example.com", "company_id": str(uuid4())},
        {},
    ],
)
def test_input(client: TestClient, payload: dict) -> None:
    assert (
        client.post(
            f"/companies/{COMPANY_ID}/member-invitations", json=payload
        ).status_code
        == 422
    )


def test_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def create(**kwargs):
        assert kwargs["owner"] == OWNER
        assert kwargs["email"] == "member@example.com"
        return application.CreatedInvitation(
            uuid4(), COMPANY_ID, kwargs["email"], datetime.now(UTC), "test-token"
        )

    monkeypatch.setattr(api, "create_member_invitation", create)
    response = client.post(
        f"/companies/{COMPANY_ID}/member-invitations",
        json={"email": " MEMBER@example.com "},
    )
    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json()["role"] == "member"
    assert "token_hash" not in response.json()


def seed_owner(session: Session) -> CurrentUser:
    company_id, owner_id = uuid4(), uuid4()
    email = f"{owner_id}@example.com"
    with session.begin():
        session.add(Company(id=company_id, name="Member invitation test"))
        session.flush()
        session.add(
            User(
                id=owner_id,
                company_id=company_id,
                email=email,
                password_hash="test-only",
                role="company_owner",
            )
        )
    return CurrentUser(owner_id, company_id, email, "company_owner", "active")


def test_postgres_member_onboarding(database_session: Session) -> None:
    session = database_session
    owner = seed_owner(session)
    email = f"{uuid4()}@example.com"
    invitation = application.create_member_invitation(
        session, owner.company_id, owner, email, 24
    )
    password = "member-test-password"
    user = application.accept_invitation(session, invitation.token, password)
    assert user.role == "member" and user.company_id == owner.company_id
    assert user.email == email
    with session.begin():
        assert verify_password(password, session.get(User, user.id).password_hash)
        assert session.get(Invitation, invitation.id).accepted_at is not None
        assert session.get(User, owner.id).role == "company_owner"
    with pytest.raises(application.InvalidInvitationError):
        application.accept_invitation(session, invitation.token, password)


def test_postgres_duplicate_and_expired(database_session: Session) -> None:
    session = database_session
    owner = seed_owner(session)
    email = f"{uuid4()}@example.com"
    first = application.create_member_invitation(
        session, owner.company_id, owner, email, 24
    )
    with pytest.raises(application.InvitationConflictError, match="pending"):
        application.create_member_invitation(
            session, owner.company_id, owner, email, 24
        )
    other = application.create_member_invitation(
        session, owner.company_id, owner, f"{uuid4()}@example.com", 24
    )
    assert other.id != first.id
    with session.begin():
        row = session.get(Invitation, first.id)
        row.created_at = datetime.now(UTC) - timedelta(days=2)
        row.expires_at = datetime.now(UTC) - timedelta(days=1)
    replacement = application.create_member_invitation(
        session, owner.company_id, owner, email, 24
    )
    assert replacement.token != first.token


@pytest.mark.parametrize("scenario", ["inactive", "registered", "other_company"])
def test_postgres_creation_rejections(database_session: Session, scenario: str) -> None:
    session = database_session
    owner = seed_owner(session)
    target_id = owner.company_id
    email = f"{uuid4()}@example.com"
    with session.begin():
        if scenario == "inactive":
            session.get(Company, target_id).status = "inactive"
        elif scenario == "registered":
            email = owner.email
        else:
            target_id = uuid4()
    expected = (
        application.InvitationPermissionError
        if scenario == "other_company"
        else application.InvitationConflictError
    )
    with pytest.raises(expected):
        application.create_member_invitation(session, target_id, owner, email, 24)
    with session.begin():
        assert (
            session.scalar(
                select(Invitation.id).where(Invitation.company_id == owner.company_id)
            )
            is None
        )
