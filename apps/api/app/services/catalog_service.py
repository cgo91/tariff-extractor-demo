"""Tariff catalog use cases."""

from __future__ import annotations

from app.domain.errors import NotFoundError
from app.domain.models import TariffItem
from app.repositories.base import TariffItemRepository

MAX_SEARCH_RESULTS = 15


class CatalogService:
    """Searches the TIGIE catalog on behalf of the UI and the classifier."""

    def __init__(self, tariff_item_repository: TariffItemRepository) -> None:
        self._tariff_items = tariff_item_repository

    async def search(self, query: str, limit: int = MAX_SEARCH_RESULTS) -> list[TariffItem]:
        """Return up to ``limit`` tariff items ranked by relevance."""
        capped = min(max(limit, 1), MAX_SEARCH_RESULTS)
        return await self._tariff_items.search_by_text(query, capped)

    async def find_candidates(
        self, keywords: list[str], limit: int = MAX_SEARCH_RESULTS
    ) -> list[TariffItem]:
        """Build the candidate list handed to Claude during classification.

        Each keyword is searched separately and the results are merged while
        preserving relevance order, because a single concatenated query tends to
        return only items matching every term.
        """
        merged: dict[tuple[str, str], TariffItem] = {}
        for keyword in keywords:
            for item in await self._tariff_items.search_by_text(keyword, limit):
                merged.setdefault((item.tariff_code, item.nico), item)
                if len(merged) >= limit:
                    return list(merged.values())
        return list(merged.values())

    async def get_item(self, tariff_code: str, nico: str) -> TariffItem:
        """Return one tariff item by its natural key.

        Raises:
            NotFoundError: when the pair does not exist in the catalog.
        """
        item = await self._tariff_items.get_by_code(tariff_code, nico)
        if item is None:
            raise NotFoundError(
                f"La fracción {tariff_code} con NICO {nico} no existe en el catálogo"
            )
        return item
