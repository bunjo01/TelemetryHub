from typing import cast

from fastapi import Request
from sqlalchemy import Engine


def get_database_engine(request: Request) -> Engine:
    return cast(Engine, request.app.state.database_engine)
