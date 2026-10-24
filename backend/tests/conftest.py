import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def pytest_configure() -> None:
    if "TEST_DATABASE_URL" in os.environ:
        return

    env_path = Path(__file__).resolve().parents[1] / ".env"
    url = dotenv_values(env_path).get("TEST_DATABASE_URL")
    if url:
        os.environ["TEST_DATABASE_URL"] = url


@pytest.fixture
def database_session() -> Iterator[Session]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL test database")
    engine = create_engine(
        url,
        hide_parameters=True,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with Session(
                    bind=connection, join_transaction_mode="create_savepoint"
                ) as session:
                    yield session
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
