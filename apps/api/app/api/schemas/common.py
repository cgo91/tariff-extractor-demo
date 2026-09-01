"""Shared response DTOs."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Uniform error envelope produced by the domain exception handler."""

    code: str
    message: str


class HealthResponse(BaseModel):
    """Liveness payload returned by ``GET /health``."""

    status: str
    database: str
    catalog_items: int


class OperationDefaultsResponse(BaseModel):
    """Values the operation form is preloaded with (RF-07)."""

    exchange_rate: float
    origin_country: str
    importer_rfc: str
    importer_legal_name: str
    supplier_name: str
    supplier_country: str


class ConfigResponse(BaseModel):
    """Server-side settings the UI needs in order to behave consistently."""

    confidence_threshold: float
    max_upload_bytes: int
    defaults: OperationDefaultsResponse
