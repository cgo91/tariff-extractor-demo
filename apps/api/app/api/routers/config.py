"""Client configuration endpoint.

Keeps the review threshold and the demo defaults in one place — the server —
so the UI never hard-codes a value that ``.env`` is supposed to own.
"""

from fastapi import APIRouter

from app.api.schemas.common import (
    ConfigResponse,
    OperationDefaultsResponse,
)
from app.core.dependencies import CurrentUserDep, SettingsDep

router = APIRouter(prefix="/config", tags=["system"])


@router.get("", response_model=ConfigResponse)
async def read_config(current_user: CurrentUserDep, settings: SettingsDep) -> ConfigResponse:
    """Return the thresholds and form defaults the frontend needs."""
    return ConfigResponse(
        confidence_threshold=settings.confidence_threshold,
        max_upload_bytes=settings.max_upload_bytes,
        defaults=OperationDefaultsResponse(
            exchange_rate=settings.default_exchange_rate,
            origin_country=settings.default_origin_country,
            importer_rfc=settings.default_importer_rfc,
            importer_legal_name=settings.default_importer_name,
            supplier_name=settings.default_supplier_name,
            supplier_country=settings.default_supplier_country,
        ),
    )
