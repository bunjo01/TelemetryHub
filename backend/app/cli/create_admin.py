import sys
import warnings
from getpass import GetPassWarning, getpass

from psycopg.errors import UniqueViolation
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings
from app.infrastructure.database import create_database_engine
from app.infrastructure.models.company import Company  # noqa: F401
from app.infrastructure.models.user import User
from app.infrastructure.passwords import hash_password


def read_email() -> str:
    raw_email = input("Email: ").strip().lower()

    try:
        email = str(TypeAdapter(EmailStr).validate_python(raw_email)).lower()
    except ValidationError:
        raise ValueError("Enter a valid email address.") from None

    if len(email) > 254:
        raise ValueError("Email must contain at most 254 characters.")

    return email


def read_password() -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("error", GetPassWarning)
        password = getpass("Password: ")
        confirmation = getpass("Confirm password: ")

    if not 15 <= len(password) <= 128:
        raise ValueError("Password must contain between 15 and 128 characters.")

    if password != confirmation:
        raise ValueError("Passwords do not match.")

    return password


def save_admin(engine: Engine, email: str, password_hash: str) -> None:
    with Session(engine) as session:
        with session.begin():
            user = User(
                email=email,
                password_hash=password_hash,
                role="system_admin",
                status="active",
                company_id=None,
            )
            session.add(user)


def main() -> int:
    try:
        # Required settings are loaded from the environment.
        settings = Settings()  # pyright: ignore[reportCallIssue]
    except ValidationError:
        print("Invalid configuration. Check your backend .env file.", file=sys.stderr)
        return 1

    try:
        email = read_email()
        password = read_password()
    except GetPassWarning:
        print(
            "Hidden password input is unavailable. Run in an interactive terminal.",
            file=sys.stderr,
        )
        return 1
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nAdministrator creation cancelled.", file=sys.stderr)
        return 1

    password_hash = hash_password(password)

    try:
        engine = create_database_engine(settings)
        try:
            save_admin(engine, email, password_hash)
        finally:
            engine.dispose()
    except IntegrityError as error:
        if (
            isinstance(error.orig, UniqueViolation)
            and error.orig.diag.constraint_name == "uq_users_email"
        ):
            print("Email already exists.", file=sys.stderr)
        else:
            print(
                "Administrator creation failed: a database constraint was violated.",
                file=sys.stderr,
            )
        return 1
    except SQLAlchemyError:
        print(
            "Database operation failed. Check database availability and permissions.",
            file=sys.stderr,
        )
        return 1

    print("System administrator created successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
