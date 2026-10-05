from sqlalchemy.orm import Session

from app.infrastructure.repositories.companies import CurrentCompany, insert_company


def create_company(session: Session, name: str) -> CurrentCompany:
    with session.begin():
        company = insert_company(session=session, name=name)
    return company
