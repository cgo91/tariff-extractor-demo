"""Database seeding entry point.

Run with::

    docker compose exec api python -m app.seed.seed

The script is idempotent: the catalog is replaced wholesale and the demo user is
upserted, so repeated runs converge on the same state.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from app.core.config import Settings, get_settings
from app.core.security import PasswordHasher
from app.domain.models import User
from app.repositories.base import TariffItemRepository, UserRepository
from app.repositories.mongo import (
    MongoConnection,
    MongoTariffItemRepository,
    MongoUserRepository,
)
from app.seed.sources import CatalogSource, ExcelCatalogSource, JsonCatalogSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed")


def _default_of(field_name: str) -> object:
    """Built-in default of a setting, used to spot a variable that never arrived."""
    return Settings.model_fields[field_name].default


def select_catalog_source(settings: Settings) -> CatalogSource:
    """Prefer the official spreadsheets, fall back to the curated JSON.

    The Excel workbooks are not committed to the repository, so this keeps the
    demo runnable out of the box while still using real SAT data the moment the
    files are dropped into ``data/``.
    """
    excel = ExcelCatalogSource(settings.sat_excel_path, settings.snice_excel_path)
    if excel.is_available():
        return excel

    logger.info(
        "No se encontró %s; se usará el catálogo curado.", settings.sat_excel_path
    )
    return JsonCatalogSource(settings.catalog_json_path)


async def seed_catalog(repository: TariffItemRepository, source: CatalogSource) -> int:
    """Load the catalog and (re)create its indexes."""
    if not source.is_available():
        raise FileNotFoundError(f"La fuente del catálogo no está disponible: {source.name}")

    items = source.load()
    if not items:
        raise ValueError(f"La fuente {source.name} no devolvió ninguna fracción")

    stored = await repository.replace_all(items)
    await repository.ensure_indexes()
    return stored


async def seed_user(
    repository: UserRepository, hasher: PasswordHasher, settings: Settings
) -> User:
    """Create or refresh the single demo user (no sign-up exists in the MVP).

    The password is reported by length, never by value: the seed log is read
    over someone's shoulder during a demo.
    """
    # A missing SEED_USER_PASSWORD does not fail: pydantic falls back to the
    # field default and the seed writes a user whose password is not the one
    # the operator configured. The seed cannot tell an absent variable from one
    # explicitly set to the same value, so it reports the fact, not the cause.
    if settings.seed_user_password == _default_of("seed_user_password"):
        logger.warning(
            "La contraseña sembrada es la de por defecto del código. Si esperabas "
            "otra, SEED_USER_PASSWORD no llegó a este proceso."
        )

    logger.info(
        "Sembrando usuario %s (contraseña de %d caracteres)",
        settings.seed_user_email,
        len(settings.seed_user_password),
    )

    user = User(
        email=settings.seed_user_email,
        password_hash=hasher.hash(settings.seed_user_password),
    )
    return await repository.upsert_by_email(user)


async def run() -> None:
    """Seed the catalog and the demo user against the configured database."""
    settings = get_settings()
    connection = MongoConnection(settings.mongo_uri, settings.mongo_db)
    await connection.connect()

    try:
        database = connection.database
        source = select_catalog_source(settings)
        logger.info("Fuente del catálogo: %s", source.name)

        stored = await seed_catalog(MongoTariffItemRepository(database), source)
        logger.info("Catálogo cargado: %d fracciones", stored)

        user = await seed_user(MongoUserRepository(database), PasswordHasher(), settings)
        logger.info("Usuario listo: %s", user.email)
        logger.info("Seed completado.")
    finally:
        await connection.close()


def main() -> int:
    """Console entry point returning a process exit code."""
    try:
        asyncio.run(run())
    except Exception as exc:  # noqa: BLE001 - top level reporting
        logger.error("El seed falló: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
