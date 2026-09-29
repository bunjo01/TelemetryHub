import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_database_engine
from app.infrastructure.database import check_database_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/ready",
    responses={503: {"description": "Database unavailable"}},
)
def ready(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> dict[str, str]:
    try:
        check_database_connection(engine)
    except SQLAlchemyError as exc:
        logger.warning(
            "Database readiness check failed", extra={"error_type": type(exc).__name__}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc

    return {"status": "ready"}
