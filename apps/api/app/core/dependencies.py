"""Dependency injection wiring.

This is the single module that knows which concrete implementation backs each
abstraction. Routers and services only ever see the interfaces, which is what
keeps them substitutable in tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.security import JwtTokenService, PasswordHasher
from app.domain.errors import AuthenticationError
from app.domain.models import User
from app.repositories.base import OperationRepository, TariffItemRepository, UserRepository
from app.repositories.mongo import (
    MongoOperationRepository,
    MongoTariffItemRepository,
    MongoUserRepository,
)
from app.services.auth_service import AuthService
from app.services.catalog_service import CatalogService

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pymongo.asynchronous.database import AsyncDatabase

# ``auto_error=False`` lets us raise our own 401 instead of FastAPI's default
# 403 when the Authorization header is missing, as required by RF-01.
_bearer_scheme = HTTPBearer(auto_error=False)

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_database(request: Request) -> AsyncDatabase:
    """Return the Mongo database opened during application startup."""
    return request.app.state.mongo.database


DatabaseDep = Annotated["AsyncDatabase", Depends(get_database)]


# --- Repositories ----------------------------------------------------------


def get_user_repository(database: DatabaseDep) -> UserRepository:
    return MongoUserRepository(database)


def get_tariff_item_repository(database: DatabaseDep) -> TariffItemRepository:
    return MongoTariffItemRepository(database)


def get_operation_repository(database: DatabaseDep) -> OperationRepository:
    return MongoOperationRepository(database)


# --- Infrastructure collaborators ------------------------------------------


def get_password_hasher() -> PasswordHasher:
    return PasswordHasher()


def get_token_service(settings: SettingsDep) -> JwtTokenService:
    return JwtTokenService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_hours=settings.jwt_expire_hours,
    )


# --- Services --------------------------------------------------------------


def get_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    token_service: Annotated[JwtTokenService, Depends(get_token_service)],
) -> AuthService:
    return AuthService(user_repository, password_hasher, token_service)


def get_catalog_service(
    tariff_item_repository: Annotated[TariffItemRepository, Depends(get_tariff_item_repository)],
) -> CatalogService:
    return CatalogService(tariff_item_repository)


# --- Security --------------------------------------------------------------


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve the authenticated user, or raise a 401.

    Every router except ``/auth/login`` and ``/health`` depends on this.
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Falta el encabezado Authorization")
    return await auth_service.get_user_from_token(credentials.credentials)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]
