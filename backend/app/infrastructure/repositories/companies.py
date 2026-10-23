from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.models.company import Company


@dataclass(frozen=True)
class CurrentCompany:
    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


def insert_company(session: Session, name: str) -> CurrentCompany:
    """Insert a company using the caller's transaction and normalized name."""
    company = Company(name=name)
    session.add(company)
    session.flush()

    return CurrentCompany(
        id=company.id,
        name=company.name,
        status=company.status,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


@dataclass(frozen=True)
class CompanyOption:
    id: UUID
    name: str


def search_companies(
    session: Session, query: str, limit: int, offset: int
) -> list[CompanyOption]:
    """Read a bounded page of active companies, treating search text literally."""
    statement = (
        select(Company.id, Company.name)
        .where(Company.status == "active")
        .order_by(func.lower(Company.name), Company.id)
        .offset(offset)
        .limit(limit)
    )
    if query:
        statement = statement.where(Company.name.icontains(query, autoescape=True))
    return [CompanyOption(row.id, row.name) for row in session.execute(statement)]


def read_company_status_for_device_operation(
    session: Session,
    company_id: UUID,
) -> str | None:
    statement = (
        select(Company.status)
        .where(Company.id == company_id)
        .with_for_update(read=True)
    )
    return session.scalar(statement)
