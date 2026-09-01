"""FastAPI application factory and process lifecycle."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import auth as auth_router
from app.api.routers import catalog as catalog_router
from app.api.routers import operations as operations_router
from app.api.schemas.common import HealthResponse
from app.core.config import get_settings
from app.core.dependencies import get_tariff_item_repository
from app.domain.errors import DomainError
from app.repositories.base import TariffItemRepository
from app.repositories.mongo import MongoConnection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the Mongo connection on startup and close it on shutdown."""
    settings = get_settings()
    connection = MongoConnection(settings.mongo_uri, settings.mongo_db)
    await connection.connect()
    app.state.mongo = connection
    logger.info("Connected to MongoDB database %s", settings.mongo_db)

    # Directories are created eagerly so the first upload never fails on a
    # missing folder when the volume is freshly mounted.
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.pedimento_dir.mkdir(parents=True, exist_ok=True)

    try:
        yield
    finally:
        await connection.close()
        logger.info("MongoDB connection closed")


def create_app() -> FastAPI:
    """Build and configure the ASGI application."""
    settings = get_settings()

    app = FastAPI(
        title="Asistente de clasificación arancelaria y pedimento",
        description=(
            "API del MVP: foto de producto -> extracción -> fracción/NICO -> pedimento PDF. "
            "Documento simulado con fines de demostración."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        """Translate any domain failure into its HTTP counterpart."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )

    app.include_router(auth_router.router)
    app.include_router(catalog_router.router)
    app.include_router(operations_router.router)

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health(
        tariff_items: Annotated[
            TariffItemRepository, Depends(get_tariff_item_repository)
        ],
    ) -> HealthResponse:
        """Report liveness plus whether the catalog has been seeded."""
        count = await tariff_items.count()
        return HealthResponse(status="ok", database="connected", catalog_items=count)

    return app


app = create_app()
