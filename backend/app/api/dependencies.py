from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session


def get_database_engine(request: Request) -> Engine:
    return cast(Engine, request.app.state.database_engine)


def get_database_session(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
