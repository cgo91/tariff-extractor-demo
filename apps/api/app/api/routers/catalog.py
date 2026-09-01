"""Tariff catalog endpoints (RF-02)."""

from fastapi import APIRouter, Query

from app.api.schemas.catalog import CatalogSearchResponse, TariffItemResponse
from app.core.dependencies import CatalogServiceDep, CurrentUserDep

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/search", response_model=CatalogSearchResponse)
async def search_catalog(
    current_user: CurrentUserDep,
    catalog_service: CatalogServiceDep,
    q: str = Query(min_length=2, description="Free-text query in Spanish"),
    limit: int = Query(default=15, ge=1, le=15),
) -> CatalogSearchResponse:
    """Return up to 15 tariff items ranked by relevance."""
    items = await catalog_service.search(q, limit)
    return CatalogSearchResponse(
        query=q,
        count=len(items),
        results=[TariffItemResponse.from_domain(item) for item in items],
    )
