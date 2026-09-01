"""MongoDB implementation of :class:`TariffItemRepository`."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from pymongo import ASCENDING, TEXT

from app.domain.models import TariffItem
from app.repositories.base import TariffItemRepository

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pymongo.asynchronous.database import AsyncDatabase

COLLECTION_NAME = "tariff_items"

# Words that add no discriminating power to a catalog search.
_STOP_WORDS = {
    "de", "la", "el", "los", "las", "un", "una", "con", "para", "por", "del",
    "y", "o", "en", "a", "al",
}


class MongoTariffItemRepository(TariffItemRepository):
    """Stores the TIGIE catalog in the ``tariff_items`` collection."""

    def __init__(self, database: AsyncDatabase) -> None:
        self._collection = database[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        """Create the Spanish text index and the natural-key unique index."""
        await self._collection.create_index(
            [("description", TEXT), ("heading_description", TEXT)],
            name="tariff_text_idx",
            default_language="spanish",
            weights={"description": 10, "heading_description": 3},
        )
        await self._collection.create_index(
            [("tariff_code", ASCENDING), ("nico", ASCENDING)],
            name="tariff_natural_key_idx",
            unique=True,
        )

    async def replace_all(self, items: Iterable[TariffItem]) -> int:
        """Wipe and reload the catalog; returns how many items were stored."""
        documents = [item.model_dump() for item in items]
        await self._collection.delete_many({})
        if documents:
            await self._collection.insert_many(documents)
        return len(documents)

    async def count(self) -> int:
        return await self._collection.count_documents({})

    async def search_by_text(self, query: str, limit: int = 15) -> list[TariffItem]:
        """Rank items with the Mongo text index, falling back to regex.

        The text index misses partial words ("audif" will not match
        "audífonos"), so an accent-tolerant regex pass rescues those queries
        instead of returning an empty candidate list to the classifier.
        """
        cleaned = query.strip()
        if not cleaned:
            return []

        results = await self._text_search(cleaned, limit)
        if results:
            return results
        return await self._regex_search(cleaned, limit)

    async def get_by_code(self, tariff_code: str, nico: str | None = None) -> TariffItem | None:
        criteria: dict[str, Any] = {"tariff_code": tariff_code}
        if nico is not None:
            criteria["nico"] = nico
        document = await self._collection.find_one(criteria)
        return TariffItem(**_strip_id(document)) if document else None

    async def find_by_codes(self, tariff_codes: Iterable[str]) -> list[TariffItem]:
        codes = list(tariff_codes)
        if not codes:
            return []
        cursor = self._collection.find({"tariff_code": {"$in": codes}})
        return [TariffItem(**_strip_id(doc)) async for doc in cursor]

    # --- internals ---------------------------------------------------------

    async def _text_search(self, query: str, limit: int) -> list[TariffItem]:
        cursor = (
            self._collection.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}},
            )
            .sort([("score", {"$meta": "textScore"})])
            .limit(limit)
        )
        return [TariffItem(**_strip_id(doc, extra={"score"})) async for doc in cursor]

    async def _regex_search(self, query: str, limit: int) -> list[TariffItem]:
        terms = [
            re.escape(term)
            for term in query.lower().split()
            if len(term) > 2 and term not in _STOP_WORDS
        ]
        if not terms:
            return []
        pattern = "|".join(terms)
        criteria = {
            "$or": [
                {"description": {"$regex": pattern, "$options": "i"}},
                {"heading_description": {"$regex": pattern, "$options": "i"}},
            ]
        }
        cursor = self._collection.find(criteria).limit(limit)
        return [TariffItem(**_strip_id(doc)) async for doc in cursor]


def _strip_id(document: dict[str, Any], extra: set[str] | None = None) -> dict[str, Any]:
    """Drop Mongo-only fields before building a domain model."""
    ignored = {"_id"} | (extra or set())
    return {key: value for key, value in document.items() if key not in ignored}
