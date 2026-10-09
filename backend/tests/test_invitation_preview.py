from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api import dependencies
from app.api import invitations as api
from app.application import invitations as application
from app.infrastructure.repositories.invitations import InvitationDetails
from app.main import handle_request_validation_error

TOKEN = "a" * 43


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(api.acceptance_router)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.dependency_overrides[dependencies.get_database_session] = lambda: None
    with TestClient(app) as client:
        yield client


def test_public_preview(client, monkeypatch):
    expires = datetime.now(UTC) + timedelta(hours=1)

    def preview(*, session, token):
        assert session is None and token == TOKEN
        return application.InvitationPreview("owner@example.com", expires)

    monkeypatch.setattr(api, "preview_invitation", preview)
    response = client.post("/invitations/preview", json={"token": TOKEN})
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "email": "owner@example.com",
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
    }


@pytest.mark.parametrize(
    "payload", [{}, {"token": "short"}, {"token": TOKEN, "email": "bad"}]
)
def test_invalid_input_is_redacted(client, payload):
    response = client.post("/invitations/preview", json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data."}
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "error,status",
    [
        (application.InvalidInvitationError(), 400),
        (OperationalError("private", {}, Exception("private")), 503),
    ],
)
def test_preview_errors(client, monkeypatch, error, status):
    def fail(**kwargs):
        raise error

    monkeypatch.setattr(api, "preview_invitation", fail)
    response = client.post("/invitations/preview", json={"token": TOKEN})
    assert response.status_code == status
    assert response.headers["Cache-Control"] == "no-store"
    assert "private" not in response.text


@pytest.mark.parametrize(
    "state", ["valid", "unknown", "expired", "used", "future", "unsupported"]
)
def test_preview_checks_validity_without_writing(monkeypatch, state):
    import hashlib

    now = datetime.now(UTC)
    invitation = InvitationDetails(
        uuid4(),
        uuid4(),
        "owner@example.com",
        "system_admin" if state == "unsupported" else "company_owner",
        now + timedelta(hours=1) if state == "future" else now - timedelta(hours=1),
        now - timedelta(seconds=1) if state == "expired" else now + timedelta(hours=2),
        now if state == "used" else None,
    )
    session = MagicMock()

    def find(actual_session, token_hash):
        assert actual_session is session
        assert token_hash == hashlib.sha256(TOKEN.encode()).hexdigest()
        return None if state == "unknown" else invitation

    monkeypatch.setattr(application.repository, "find_invitation", find)
    if state == "valid":
        result = application.preview_invitation(session, TOKEN)
        assert result.email == invitation.email
    else:
        with pytest.raises(application.InvalidInvitationError):
            application.preview_invitation(session, TOKEN)
    session.add.assert_not_called()
    session.execute.assert_not_called()
