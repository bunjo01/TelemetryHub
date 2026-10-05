import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import BoundedSemaphore

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.api.auth import router as auth_router
from app.api.companies import router as companies_router
from app.api.health import router as health_router
from app.config import Settings
from app.infrastructure.database import create_database_engine
from app.infrastructure.passwords import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Required settings are loaded from environment variables or .env.
    settings = Settings()  # pyright: ignore[reportCallIssue]
    engine = create_database_engine(settings)

    try:
        app.state.settings = settings
        app.state.database_engine = engine
        app.state.login_slots = BoundedSemaphore(settings.login_max_concurrent)
        app.state.dummy_password_hash = await run_in_threadpool(
            hash_password, secrets.token_urlsafe(32)
        )
        yield
    finally:
        await run_in_threadpool(engine.dispose)


app = FastAPI(title="IoTMonitor API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Invalid request data."})


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(companies_router)
