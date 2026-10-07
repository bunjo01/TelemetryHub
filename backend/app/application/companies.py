from sqlalchemy.orm import Session

from app.infrastructure.repositories.companies import (
    CompanyOption,
    CurrentCompany,
    insert_company,
    search_companies,
)


def create_company(session: Session, name: str) -> CurrentCompany:
    with session.begin():
        company = insert_company(session=session, name=name)
    return company


def list_company_options(
    session: Session, query: str, limit: int, offset: int
) -> tuple[list[CompanyOption], bool]:
    with session.begin():
        results = search_companies(session, query.strip(), limit + 1, offset)
    return results[:limit], len(results) > limit
