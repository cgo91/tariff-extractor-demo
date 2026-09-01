"""Shared pytest fixtures.

Every fixture here builds the object graph from in-memory implementations, so
the suite runs without MongoDB, without the Anthropic API and without any
environment variable being set.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pytest
from PIL import Image

from app.core.security import JwtTokenService, PasswordHasher
from app.domain.models import TariffItem, User
from app.repositories.memory import (
    InMemoryOperationRepository,
    InMemoryTariffItemRepository,
    InMemoryUserRepository,
)
from app.services.auth_service import AuthService
from app.services.catalog_service import CatalogService
from app.services.classification_service import ClassificationService
from app.services.extraction_service import ExtractionService
from app.services.image_processing import ImageProcessor
from app.services.operation_service import OperationService
from tests.doubles import (
    InMemoryFileStorage,
    StubTariffClassifier,
    StubVisionExtractor,
)

CATALOG_RELATIVE_PATH = Path("data") / "catalog" / "tariff_items.json"


def _locate_catalog() -> Path:
    """Find the curated catalog from either the repo checkout or the container.

    Inside Docker the file is mounted at the configured absolute path; on a
    developer machine it sits a few directories above this file.
    """
    configured = Path(os.environ.get("CATALOG_JSON_PATH", "/data/catalog/tariff_items.json"))
    if configured.is_file():
        return configured

    for parent in Path(__file__).resolve().parents:
        candidate = parent / CATALOG_RELATIVE_PATH
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(f"No se encontró {CATALOG_RELATIVE_PATH}")


CATALOG_PATH = _locate_catalog()

DEMO_EMAIL = "demo@aduana.mx"
DEMO_PASSWORD = "demo1234"

# Mirrors CONFIDENCE_THRESHOLD in .env.example.
CONFIDENCE_THRESHOLD = 0.6


@pytest.fixture
def password_hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture
def token_service() -> JwtTokenService:
    return JwtTokenService(
        secret="test-secret-that-is-at-least-32-bytes-long",
        algorithm="HS256",
        expire_hours=8,
    )


@pytest.fixture
def catalog_items() -> list[TariffItem]:
    """Load the curated catalog shipped with the repository."""
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return [TariffItem(**item) for item in payload["items"]]


@pytest.fixture
def tariff_item_repository(catalog_items: list[TariffItem]) -> InMemoryTariffItemRepository:
    return InMemoryTariffItemRepository(catalog_items)


@pytest.fixture
def operation_repository() -> InMemoryOperationRepository:
    return InMemoryOperationRepository()


@pytest.fixture
async def user_repository(password_hasher: PasswordHasher) -> InMemoryUserRepository:
    """A repository already holding the seeded demo user."""
    repository = InMemoryUserRepository()
    await repository.insert(
        User(email=DEMO_EMAIL, password_hash=password_hasher.hash(DEMO_PASSWORD))
    )
    return repository


@pytest.fixture
def auth_service(
    user_repository: InMemoryUserRepository,
    password_hasher: PasswordHasher,
    token_service: JwtTokenService,
) -> AuthService:
    return AuthService(user_repository, password_hasher, token_service)


@pytest.fixture
def catalog_service(tariff_item_repository: InMemoryTariffItemRepository) -> CatalogService:
    return CatalogService(tariff_item_repository)

# --- Phase 2 fixtures: uploads, extraction and classification ---------------


@pytest.fixture
def file_storage() -> InMemoryFileStorage:
    return InMemoryFileStorage()


@pytest.fixture
def image_processor() -> ImageProcessor:
    return ImageProcessor(max_bytes=10 * 1024 * 1024)


@pytest.fixture
def demo_user() -> User:
    """A user object standing in for the authenticated caller."""
    return User(id="user-1", email=DEMO_EMAIL, password_hash="unused")


@pytest.fixture
def jpeg_bytes() -> bytes:
    """A tiny but genuine JPEG, so the processor exercises real decoding."""
    buffer = io.BytesIO()
    Image.new("RGB", (48, 32), color=(180, 40, 60)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def png_bytes() -> bytes:
    """A tiny PNG with an alpha channel."""
    buffer = io.BytesIO()
    Image.new("RGBA", (24, 24), color=(10, 120, 90, 128)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def operation_service(
    operation_repository: InMemoryOperationRepository,
    file_storage: InMemoryFileStorage,
    image_processor: ImageProcessor,
) -> OperationService:
    return OperationService(operation_repository, file_storage, image_processor)


@pytest.fixture
def vision_extractor() -> StubVisionExtractor:
    return StubVisionExtractor()


@pytest.fixture
def tariff_classifier() -> StubTariffClassifier:
    return StubTariffClassifier()


@pytest.fixture
def extraction_service(
    operation_service: OperationService,
    operation_repository: InMemoryOperationRepository,
    vision_extractor: StubVisionExtractor,
) -> ExtractionService:
    return ExtractionService(operation_service, operation_repository, vision_extractor)


@pytest.fixture
def classification_service(
    operation_repository: InMemoryOperationRepository,
    catalog_service: CatalogService,
    tariff_classifier: StubTariffClassifier,
) -> ClassificationService:
    return ClassificationService(
        operation_repository, catalog_service, tariff_classifier, CONFIDENCE_THRESHOLD
    )
