from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session, require_system_admin
from app.api.schemas.companies import (
    CompanyOptionResponse,
    CompanyResponse,
    CompanySearchResponse,
    CreateCompanyRequest,
)
from app.application.companies import create_company, list_company_options

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CompanyResponse,
    dependencies=[Depends(require_system_admin)],
    responses={
        401: {"description": "Invalid or missing credentials"},
        403: {"description": "System administrator access required"},
        503: {"description": "Company creation temporarily unavailable"},
    },
)
def create_company_endpoint(
    payload: CreateCompanyRequest,
    session: Annotated[Session, Depends(get_database_session)],
) -> CompanyResponse:
    try:
        company = create_company(session=session, name=payload.name)
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Company creation temporarily unavailable.",
        ) from None

    return CompanyResponse(
        id=company.id,
        name=company.name,
        status=company.status,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


@router.get(
    "",
    response_model=CompanySearchResponse,
    dependencies=[Depends(require_system_admin)],
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Administrator access required"},
        503: {"description": "Company search temporarily unavailable"},
    },
)
def search_company_options(
    response: Response,
    session: Annotated[Session, Depends(get_database_session)],
    q: Annotated[str, Query(max_length=200)] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> CompanySearchResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        items, has_more = list_company_options(session, q, limit, offset)
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(503, "Company search temporarily unavailable.") from None
    return CompanySearchResponse(
        items=[CompanyOptionResponse(id=item.id, name=item.name) for item in items],
        has_more=has_more,
    )
