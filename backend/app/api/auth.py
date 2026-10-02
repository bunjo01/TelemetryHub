from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_database_session,
    get_dummy_password_hash,
    get_settings,
    require_login_capacity,
)
from app.api.schemas.auth import LoginRequest, TokenResponse
from app.application.authentication import (
    InvalidCredentialsError,
    authenticate_user,
)
from app.config import Settings
from app.infrastructure.tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(require_login_capacity)],
    responses={
        401: {"description": "Invalid credentials"},
        503: {"description": "Login temporarily unavailable"},
    },
)
def login(
    payload: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    dummy_password_hash: Annotated[str, Depends(get_dummy_password_hash)],
) -> TokenResponse:
    response.headers["Cache-Control"] = "no-store"

    try:
        user_id = authenticate_user(
            session=session,
            email=str(payload.email),
            password=payload.password.get_secret_value(),
            dummy_password_hash=dummy_password_hash,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"Cache-Control": "no-store"},
        ) from None
    except (OperationalError, SQLAlchemyTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login temporarily unavailable.",
            headers={"Cache-Control": "no-store"},
        ) from None

    token = create_access_token(
        user_id=user_id,
        secret_key=settings.jwt_secret_key.get_secret_value(),
        expires_in_minutes=settings.access_token_expire_minutes,
    )

    return TokenResponse(access_token=token)
