"""Tests for the tariff catalog (RF-02).

These run against the real curated catalog file, so they double as a regression
check that the seed data still covers every demo product listed in vision.md.
"""

from __future__ import annotations

import pytest

from app.domain.errors import NotFoundError
from app.domain.models import TariffItem
from app.services.catalog_service import MAX_SEARCH_RESULTS, CatalogService


class TestCuratedCatalog:
    def test_covers_every_demo_subheading(self, catalog_items: list[TariffItem]) -> None:
        """Each product in vision.md must have at least one candidate."""
        expected_subheadings = {
            "851830",  # audifonos bluetooth
            "851821",  # bocina bluetooth (un altavoz)
            "851822",  # bocina bluetooth (varios altavoces)
            "850440",  # cargador USB de pared
            "854442",  # cable USB con conectores
            "847160",  # mouse / teclado
            "850760",  # power bank
            "851713",  # smartphone
            "851762",  # router / smartwatch conectado
            "910212",  # smartwatch visto como reloj (caso ambiguo)
        }
        codes = {item.tariff_code for item in catalog_items}

        for subheading in expected_subheadings:
            assert any(code.startswith(subheading) for code in codes), subheading

    def test_natural_keys_are_unique(self, catalog_items: list[TariffItem]) -> None:
        keys = [(item.tariff_code, item.nico) for item in catalog_items]
        assert len(keys) == len(set(keys))

    def test_rates_are_expressed_as_fractions(self, catalog_items: list[TariffItem]) -> None:
        assert all(0.0 <= item.igi_rate <= 1.0 for item in catalog_items)
        assert all(item.iva_rate == 0.16 for item in catalog_items)

    def test_formats_the_code_for_printing(self) -> None:
        item = TariffItem(
            tariff_code="85183001", description="Audífonos", chapter="85"
        )
        assert item.formatted_code == "8518.30.01"


class TestCatalogSearch:
    async def test_finds_headphones_in_heading_8518(
        self, catalog_service: CatalogService
    ) -> None:
        results = await catalog_service.search("audífonos")

        assert results
        assert any(item.tariff_code.startswith("8518") for item in results)

    async def test_search_is_accent_insensitive(self, catalog_service: CatalogService) -> None:
        with_accent = await catalog_service.search("audífonos")
        without_accent = await catalog_service.search("audifonos")

        assert [item.tariff_code for item in with_accent] == [
            item.tariff_code for item in without_accent
        ]

    async def test_finds_routers_in_heading_8517(self, catalog_service: CatalogService) -> None:
        results = await catalog_service.search("enrutadores redes")

        assert any(item.tariff_code.startswith("851762") for item in results)

    async def test_returns_nothing_for_a_blank_query(
        self, catalog_service: CatalogService
    ) -> None:
        assert await catalog_service.search("   ") == []

    @pytest.mark.parametrize("limit", [1, 5, 99])
    async def test_never_exceeds_the_hard_cap(
        self, catalog_service: CatalogService, limit: int
    ) -> None:
        results = await catalog_service.search("eléctricos", limit)

        assert len(results) <= min(limit, MAX_SEARCH_RESULTS)


class TestCandidateBuilding:
    async def test_merges_results_across_keywords(
        self, catalog_service: CatalogService
    ) -> None:
        candidates = await catalog_service.find_candidates(
            ["audífonos", "bluetooth", "inalámbricos"]
        )

        assert candidates
        assert len(candidates) <= MAX_SEARCH_RESULTS
        keys = [(item.tariff_code, item.nico) for item in candidates]
        assert len(keys) == len(set(keys)), "candidates must be deduplicated"

    async def test_smartwatch_keywords_surface_both_readings(
        self, catalog_service: CatalogService
    ) -> None:
        """The ambiguous case needs candidates from heading 8517 and chapter 91."""
        candidates = await catalog_service.find_candidates(
            ["reloj", "pulsera", "comunicación", "inalámbrica"]
        )
        chapters = {item.chapter for item in candidates}

        assert "85" in chapters
        assert "91" in chapters


class TestCatalogLookup:
    async def test_returns_an_item_by_natural_key(
        self, catalog_service: CatalogService
    ) -> None:
        item = await catalog_service.get_item("85183001", "00")

        assert item.tariff_code == "85183001"

    async def test_raises_when_the_pair_is_unknown(
        self, catalog_service: CatalogService
    ) -> None:
        with pytest.raises(NotFoundError):
            await catalog_service.get_item("99999999", "00")
