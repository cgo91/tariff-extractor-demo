"""Response DTOs for the catalog endpoints."""

from pydantic import BaseModel

from app.domain.models import TariffItem


class TariffItemResponse(BaseModel):
    """A catalog entry as exposed by the API."""

    tariff_code: str
    formatted_code: str
    nico: str
    description: str
    heading_description: str
    chapter: str
    unit_of_measure: str
    igi_rate: float
    iva_rate: float

    @classmethod
    def from_domain(cls, item: TariffItem) -> "TariffItemResponse":
        """Build the DTO from a domain model."""
        return cls(
            tariff_code=item.tariff_code,
            formatted_code=item.formatted_code,
            nico=item.nico,
            description=item.description,
            heading_description=item.heading_description,
            chapter=item.chapter,
            unit_of_measure=item.unit_of_measure,
            igi_rate=item.igi_rate,
            iva_rate=item.iva_rate,
        )


class CatalogSearchResponse(BaseModel):
    """Envelope returned by ``GET /catalog/search``."""

    query: str
    count: int
    results: list[TariffItemResponse]
