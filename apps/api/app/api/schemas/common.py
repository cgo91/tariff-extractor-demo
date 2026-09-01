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
