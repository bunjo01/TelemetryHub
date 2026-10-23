from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import MigrationSettings
from app.infrastructure.models.base import Base
from app.infrastructure.models.company import Company  # noqa: F401
from app.infrastructure.models.device import Device  # noqa: F401
from app.infrastructure.models.invitation import Invitation  # noqa: F401
from app.infrastructure.models.user import User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Required settings come from environment variables or migrations/.env.
settings = MigrationSettings()  # pyright: ignore[reportCallIssue]

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(settings.migration_database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(
        str(settings.migration_database_url),
        poolclass=pool.NullPool,
        hide_parameters=True,
        connect_args={
            "connect_timeout": settings.migration_connect_timeout_seconds,
            "options": (
                f"-c statement_timeout={settings.migration_statement_timeout_ms} "
                f"-c lock_timeout={settings.migration_lock_timeout_ms}"
            ),
        },
    )

    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_server_default=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
