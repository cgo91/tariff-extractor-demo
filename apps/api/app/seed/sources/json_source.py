"""Curated JSON catalog source (default)."""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import TariffItem
from app.seed.sources.base import CatalogSource


class JsonCatalogSource(CatalogSource):
    """Loads the hand-curated catalog shipped in ``data/catalog``.

    Accepts either a bare JSON array or an object with an ``items`` key, so the
    file can carry provenance metadata alongside the data.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def name(self) -> str:
        return f"JSON curado ({self._path})"

    def is_available(self) -> bool:
        return self._path.is_file()

    def load(self) -> list[TariffItem]:
        with self._path.open(encoding="utf-8") as handle:
            payload = json.load(handle)

        raw_items = payload["items"] if isinstance(payload, dict) else payload
        return [TariffItem(**item) for item in raw_items]
