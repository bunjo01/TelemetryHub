from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

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
