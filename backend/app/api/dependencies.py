from collections.abc import Iterator
from threading import BoundedSemaphore
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.application.authentication import (
    CurrentUserUnavailableError,
    load_current_user,
)
from app.config import Settings
from app.infrastructure.repositories.users import CurrentUser
from app.infrastructure.tokens import (
    InvalidAccessTokenError,
    decode_access_token,
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_database_engine(request: Request) -> Engine:
    return cast(Engine, request.app.state.database_engine)


def get_database_session(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_dummy_password_hash(request: Request) -> str:
    return cast(str, request.app.state.dummy_password_hash)


def require_login_capacity(request: Request) -> Iterator[None]:
    slots = cast(
        BoundedSemaphore,
        request.app.state.login_slots,
    )

    if not slots.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login is busy. Try again shortly.",
            headers={"Retry-After": "1"},
        )

    try:
        yield
    finally:
        slots.release()


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={
            "WWW-Authenticate": "Bearer",
            "Cache-Control": "no-store",
        },
    )

    if credentials is None:
        raise unauthorized

    try:
        # Header: Authorization: Bearer eyJhbGci...
        # credentials.credentials contains only "eyJhbGci..."
        user_id = decode_access_token(
            token=credentials.credentials,
            secret_key=settings.jwt_secret_key.get_secret_value(),
        )

        return load_current_user(
            session=session,
            user_id=user_id,
        )

    except (InvalidAccessTokenError, CurrentUserUnavailableError):
        raise unauthorized from None

    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None
