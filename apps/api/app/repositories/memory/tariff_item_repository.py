"""In-memory :class:`TariffItemRepository`, used by the test suite."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

from app.domain.models import TariffItem
from app.repositories.base import TariffItemRepository


def _normalize(text: str) -> str:
    """Lowercase and strip accents so searches behave like the Spanish index."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


class InMemoryTariffItemRepository(TariffItemRepository):
    """List-backed catalog that scores items by naive term overlap."""

    def __init__(self, items: Iterable[TariffItem] | None = None) -> None:
        self._items: list[TariffItem] = list(items or [])

    async def ensure_indexes(self) -> None:
        """No-op: an in-memory list needs no indexes."""

    async def replace_all(self, items: Iterable[TariffItem]) -> int:
        self._items = list(items)
        return len(self._items)

    async def count(self) -> int:
        return len(self._items)

    async def search_by_text(self, query: str, limit: int = 15) -> list[TariffItem]:
        terms = [term for term in _normalize(query).split() if len(term) > 2]
        if not terms:
            return []

        scored: list[tuple[int, TariffItem]] = []
        for item in self._items:
            haystack = _normalize(f"{item.description} {item.heading_description}")
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]

    async def get_by_code(self, tariff_code: str, nico: str | None = None) -> TariffItem | None:
        for item in self._items:
            if item.tariff_code == tariff_code and (nico is None or item.nico == nico):
                return item
        return None

    async def find_by_codes(self, tariff_codes: Iterable[str]) -> list[TariffItem]:
        wanted = set(tariff_codes)
        return [item for item in self._items if item.tariff_code in wanted]
