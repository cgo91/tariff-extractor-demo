"""Shared pytest fixtures.

Every fixture here builds the object graph from in-memory implementations, so
the suite runs without MongoDB, without the Anthropic API and without any
environment variable being set.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.core.security import JwtTokenService, PasswordHasher
from app.domain.models import TariffItem, User
from app.repositories.memory import (
    InMemoryOperationRepository,
    InMemoryTariffItemRepository,
    InMemoryUserRepository,
)
from app.services.auth_service import AuthService
from app.services.catalog_service import CatalogService

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
