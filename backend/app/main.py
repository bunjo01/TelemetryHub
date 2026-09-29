from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from app.api.health import router as health_router
from app.config import Settings
from app.infrastructure.database import create_database_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Required settings are loaded from environment variables or .env.
    settings = Settings()  # pyright: ignore[reportCallIssue]
    engine = create_database_engine(settings)

    try:
        app.state.database_engine = engine
        yield
    finally:
        await run_in_threadpool(engine.dispose)


app = FastAPI(title="IoTMonitor API", lifespan=lifespan)

app.include_router(health_router)
