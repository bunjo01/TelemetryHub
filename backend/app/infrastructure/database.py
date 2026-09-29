from sqlalchemy import Engine, create_engine

from app.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    return create_engine(
        str(settings.database_url),
        pool_size=settings.database_pool_size,
        max_overflow=0,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={
            "connect_timeout": settings.database_pool_timeout_seconds,
            "options": (
                f"-c statement_timeout={settings.database_statement_timeout_ms}"
            ),
        },
    )
