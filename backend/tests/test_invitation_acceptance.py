import hashlib
import os
import secrets
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier, BoundedSemaphore
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api import dependencies
from app.api import invitations as api
from app.application import invitations as application
from app.infrastructure.models.company import Company
from app.infrastructure.models.invitation import Invitation
from app.infrastructure.models.user import User
from app.infrastructure.passwords import verify_password
from app.infrastructure.repositories.users import CurrentUser
from app.main import app as main_app
from app.main import handle_request_validation_error

PASSWORD = "test-only-password-with-spaces "
TOKEN = "a" * 43


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(api.acceptance_router)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.state.login_slots = BoundedSemaphore(1)
    app.dependency_overrides[dependencies.get_database_session] = lambda: None

    def unexpected_accept(**kwargs):
        pytest.fail("Invalid input must not reach acceptance")

    monkeypatch.setattr(api, "accept_invitation", unexpected_accept)
    with TestClient(app) as test_client:
        yield test_client


def test_acceptance_is_public_and_returns_only_user(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = CurrentUser(uuid4(), uuid4(), "owner@example.com", "company_owner", "active")

    def accept(**kwargs):
        assert kwargs["token"] == TOKEN
        assert kwargs["password"] == PASSWORD
        return user

    monkeypatch.setattr(api, "accept_invitation", accept)
    response = client.post(
        "/invitations/accept", json={"token": TOKEN, "password": PASSWORD}
    )
    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "id": str(user.id),
        "company_id": str(user.company_id),
        "email": user.email,
        "role": "company_owner",
        "status": "active",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"token": "short"},
        {"token": "a" * 44},
        {"token": None},
        {"password": "a" * 14},
        {"password": "a" * 129},
        {"password": None},
        {"email": "attacker@example.com"},
        {"company_id": str(uuid4())},
        {"role": "system_admin"},
    ],
)
def test_input_and_secret_redaction(client: TestClient, change: dict) -> None:
    payload = {"token": TOKEN, "password": PASSWORD, **change}
    response = client.post("/invitations/accept", json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data."}


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (application.InvalidInvitationError(), 400),
        (application.InvitationConflictError("Company already has an owner."), 409),
        (OperationalError("private", {}, Exception("private")), 503),
        (SQLAlchemyTimeoutError("private"), 503),
    ],
)
def test_error_mapping_and_capacity_release(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, error: Exception, status: int
) -> None:
    def fail(**kwargs):
        raise error

    monkeypatch.setattr(api, "accept_invitation", fail)
    response = client.post(
        "/invitations/accept", json={"token": TOKEN, "password": PASSWORD}
    )
    assert response.status_code == status
    assert response.headers["Cache-Control"] == "no-store"
    assert "private" not in response.text
    assert client.app.state.login_slots.acquire(blocking=False)
    client.app.state.login_slots.release()


def test_overload(client: TestClient) -> None:
    slots = client.app.state.login_slots
    slots.acquire()
    try:
        response = client.post(
            "/invitations/accept", json={"token": TOKEN, "password": PASSWORD}
        )
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "1"
    finally:
        slots.release()


def test_route_is_public() -> None:
    operation = main_app.openapi()["paths"]["/invitations/accept"]["post"]
    assert "201" in operation["responses"]
    assert not operation.get("security")


def seed_invitation(
    session: Session, role: str = "company_owner"
) -> tuple[Invitation, str]:
    admin_id, company_id = uuid4(), uuid4()
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    with session.begin():
        session.add(Company(id=company_id, name="Acceptance test"))
        session.add(
            User(
                id=admin_id,
                email=f"{admin_id}@example.com",
                password_hash="test-only",
                role="system_admin",
            )
        )
        session.flush()
        invitation = Invitation(
            id=uuid4(),
            company_id=company_id,
            invited_by_id=admin_id,
            email=f"{uuid4()}@example.com",
            role=role,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        session.add(invitation)
        session.flush()
        session.expunge(invitation)
    return invitation, token


@pytest.mark.parametrize("role", ["company_owner", "member"])
def test_postgres_preview_does_not_consume(
    database_session: Session, role: str
) -> None:
    invitation, token = seed_invitation(database_session, role)
    for _ in range(2):
        preview = application.preview_invitation(database_session, token)
        assert preview.email == invitation.email
        assert preview.expires_at == invitation.expires_at
    user = application.accept_invitation(database_session, token, PASSWORD)
    assert user.role == role
    with pytest.raises(application.InvalidInvitationError):
        application.preview_invitation(database_session, token)


def test_postgres_acceptance_and_reuse(database_session: Session) -> None:
    invitation, token = seed_invitation(database_session)
    user = application.accept_invitation(database_session, token, PASSWORD)
    assert user.company_id == invitation.company_id
    assert user.email == invitation.email
    assert user.role == "company_owner" and user.status == "active"
    with database_session.begin():
        stored = database_session.get(User, user.id)
        assert stored.password_hash != PASSWORD
        assert verify_password(PASSWORD, stored.password_hash)
        assert database_session.get(Invitation, invitation.id).accepted_at is not None
    with pytest.raises(application.InvalidInvitationError):
        application.accept_invitation(database_session, token, PASSWORD)


@pytest.mark.parametrize("scenario", ["unknown", "expired", "used"])
def test_unusable_tokens_do_not_hash(
    database_session: Session, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    invitation, token = seed_invitation(database_session)
    with database_session.begin():
        row = database_session.get(Invitation, invitation.id)
        if scenario == "expired":
            row.created_at = datetime.now(UTC) - timedelta(days=2)
            row.expires_at = datetime.now(UTC) - timedelta(days=1)
        elif scenario == "used":
            row.accepted_at = datetime.now(UTC)
        else:
            token = secrets.token_urlsafe(32)

    def unexpected_hash(password: str) -> str:
        pytest.fail("Unusable token reached password hashing")

    monkeypatch.setattr(application, "hash_password", unexpected_hash)
    with pytest.raises(application.InvalidInvitationError):
        application.accept_invitation(database_session, token, PASSWORD)


@pytest.mark.parametrize("scenario", ["inactive", "owner", "email"])
def test_state_is_rechecked(database_session: Session, scenario: str) -> None:
    invitation, token = seed_invitation(database_session)
    with database_session.begin():
        if scenario == "inactive":
            database_session.get(Company, invitation.company_id).status = "inactive"
        else:
            database_session.add(
                User(
                    email=invitation.email
                    if scenario == "email"
                    else f"{uuid4()}@example.com",
                    password_hash="test-only",
                    role="system_admin" if scenario == "email" else "company_owner",
                    company_id=None if scenario == "email" else invitation.company_id,
                )
            )
    with pytest.raises(application.InvitationConflictError):
        application.accept_invitation(database_session, token, PASSWORD)
    with database_session.begin():
        assert database_session.get(Invitation, invitation.id).accepted_at is None


def test_user_insert_rolls_back_if_consumption_fails(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    invitation, token = seed_invitation(database_session)

    def fail(*args):
        raise SQLAlchemyTimeoutError("test failure after user insertion")

    monkeypatch.setattr(application.repository, "mark_invitation_accepted", fail)
    with pytest.raises(SQLAlchemyTimeoutError):
        application.accept_invitation(database_session, token, PASSWORD)
    with database_session.begin():
        assert (
            database_session.scalar(
                select(User.id).where(User.email == invitation.email)
            )
            is None
        )
        assert database_session.get(Invitation, invitation.id).accepted_at is None


def test_hashing_has_no_open_transaction(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, token = seed_invitation(database_session)
    real_hash = application.hash_password

    def checked_hash(password: str) -> str:
        assert not database_session.in_transaction()
        return real_hash(password)

    monkeypatch.setattr(application, "hash_password", checked_hash)
    application.accept_invitation(database_session, token, PASSWORD)


def test_expiry_is_rechecked_after_hashing(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    invitation, token = seed_invitation(database_session)
    real_hash = application.hash_password

    def expire_during_hash(password: str) -> str:
        result = real_hash(password)

        class ExpiredClock:
            @staticmethod
            def now(tz):
                return invitation.expires_at

        monkeypatch.setattr(application, "datetime", ExpiredClock)
        return result

    monkeypatch.setattr(application, "hash_password", expire_during_hash)
    with pytest.raises(application.InvalidInvitationError):
        application.accept_invitation(database_session, token, PASSWORD)
    with database_session.begin():
        assert (
            database_session.scalar(
                select(User.id).where(User.email == invitation.email)
            )
            is None
        )
        assert database_session.get(Invitation, invitation.id).accepted_at is None


@pytest.mark.parametrize("role", ["company_owner", "member"])
def test_concurrent_acceptance(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL for PostgreSQL concurrency tests")
    engine = create_engine(
        url,
        hide_parameters=True,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
    )
    invitation = None
    try:
        # Independent connections must see committed fixtures. Delete only these
        # uniquely identified test rows in finally, in foreign-key order.
        with Session(engine) as session:
            invitation, token = seed_invitation(session, role)
        barrier = Barrier(2, timeout=10)
        real_hash = application.hash_password

        def synchronized_hash(password: str) -> str:
            result = real_hash(password)
            barrier.wait()
            return result

        monkeypatch.setattr(application, "hash_password", synchronized_hash)

        def accept() -> str:
            with Session(engine) as session:
                try:
                    application.accept_invitation(session, token, PASSWORD)
                    return "created"
                except application.InvalidInvitationError:
                    return "used"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: accept(), range(2)))
        assert sorted(results) == ["created", "used"]
        with Session(engine) as session:
            assert (
                len(
                    session.scalars(
                        select(User.id).where(User.company_id == invitation.company_id)
                    ).all()
                )
                == 1
            )
    finally:
        if invitation is not None:
            with engine.begin() as connection:
                connection.execute(
                    delete(Invitation).where(Invitation.id == invitation.id)
                )
                connection.execute(
                    delete(User).where(User.company_id == invitation.company_id)
                )
                connection.execute(
                    delete(User).where(User.id == invitation.invited_by_id)
                )
                connection.execute(
                    delete(Company).where(Company.id == invitation.company_id)
                )
        engine.dispose()
