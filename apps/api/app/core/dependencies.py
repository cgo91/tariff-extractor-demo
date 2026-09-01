"""Dependency injection wiring.

This is the single module that knows which concrete implementation backs each
abstraction. Routers and services only ever see the interfaces, which is what
keeps them substitutable in tests.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import anthropic
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.security import JwtTokenService, PasswordHasher
from app.domain.errors import AuthenticationError, LlmError
from app.domain.models import User
from app.integrations.llm.base import TariffClassifier, VisionExtractor
from app.integrations.llm.claude_client import ClaudeTariffClassifier, ClaudeVisionExtractor
from app.repositories.base import OperationRepository, TariffItemRepository, UserRepository
from app.repositories.mongo import (
    MongoOperationRepository,
    MongoTariffItemRepository,
    MongoUserRepository,
)
from app.services.auth_service import AuthService
from app.services.catalog_service import CatalogService
from app.services.classification_service import ClassificationService
from app.services.extraction_service import ExtractionService
from app.services.image_processing import ImageProcessor
from app.services.operation_service import OperationService
from app.services.storage.base import FileStorage
from app.services.storage.local_storage import LocalFileStorage

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


@lru_cache
def _build_anthropic_client(api_key: str) -> anthropic.AsyncAnthropic:
    """Build the SDK client once: it holds a connection pool worth reusing."""
    return anthropic.AsyncAnthropic(api_key=api_key)


def get_anthropic_client(settings: SettingsDep) -> anthropic.AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise LlmError(
            "Falta ANTHROPIC_API_KEY. Defínela en el archivo .env y reinicia la API."
        )
    return _build_anthropic_client(settings.anthropic_api_key)


@lru_cache
def _build_file_storage(upload_dir: Path, pedimento_dir: Path) -> FileStorage:
    """Cached because the constructor creates the directories on disk."""
    return LocalFileStorage(upload_dir, pedimento_dir)


def get_file_storage(settings: SettingsDep) -> FileStorage:
    return _build_file_storage(settings.upload_dir, settings.pedimento_dir)


def get_image_processor(settings: SettingsDep) -> ImageProcessor:
    return ImageProcessor(settings.max_upload_bytes)


def get_vision_extractor(
    client: Annotated[anthropic.AsyncAnthropic, Depends(get_anthropic_client)],
    settings: SettingsDep,
) -> VisionExtractor:
    return ClaudeVisionExtractor(
        client, settings.claude_model, settings.claude_extraction_effort
    )


def get_tariff_classifier(
    client: Annotated[anthropic.AsyncAnthropic, Depends(get_anthropic_client)],
    settings: SettingsDep,
) -> TariffClassifier:
    return ClaudeTariffClassifier(
        client, settings.claude_model, settings.claude_classification_effort
    )


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


def get_operation_service(
    operation_repository: Annotated[OperationRepository, Depends(get_operation_repository)],
    file_storage: Annotated[FileStorage, Depends(get_file_storage)],
    image_processor: Annotated[ImageProcessor, Depends(get_image_processor)],
) -> OperationService:
    return OperationService(operation_repository, file_storage, image_processor)


def get_extraction_service(
    operation_service: Annotated[OperationService, Depends(get_operation_service)],
    operation_repository: Annotated[OperationRepository, Depends(get_operation_repository)],
    extractor: Annotated[VisionExtractor, Depends(get_vision_extractor)],
) -> ExtractionService:
    return ExtractionService(operation_service, operation_repository, extractor)


def get_classification_service(
    operation_repository: Annotated[OperationRepository, Depends(get_operation_repository)],
    catalog_service: Annotated[CatalogService, Depends(get_catalog_service)],
    classifier: Annotated[TariffClassifier, Depends(get_tariff_classifier)],
    settings: SettingsDep,
) -> ClassificationService:
    return ClassificationService(
        operation_repository, catalog_service, classifier, settings.confidence_threshold
    )


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
OperationServiceDep = Annotated[OperationService, Depends(get_operation_service)]
ExtractionServiceDep = Annotated[ExtractionService, Depends(get_extraction_service)]
ClassificationServiceDep = Annotated[
    ClassificationService, Depends(get_classification_service)
]
