from collections.abc import Iterator
from threading import BoundedSemaphore
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import Settings


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
