"""Authentication endpoints (RF-01)."""

from fastapi import APIRouter, status

from app.api.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse
from app.core.dependencies import AuthServiceDep, CurrentUserDep

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> LoginResponse:
    """Exchange email and password for an 8 hour JWT."""
    token = await auth_service.login(payload.email, payload.password)
    return LoginResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
    )


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(current_user: CurrentUserDep) -> CurrentUserResponse:
    """Return the caller's identity; used to validate a stored token."""
    return CurrentUserResponse(id=str(current_user.id), email=current_user.email)
