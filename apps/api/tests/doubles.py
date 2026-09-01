"""Test doubles for the LLM and storage collaborators.

They implement the same abstract interfaces the production classes do, which is
the point of having those interfaces: the services under test cannot tell the
difference, and no network or disk is involved.
"""

from __future__ import annotations

from app.domain.errors import LlmError
from app.domain.models import (
    ClassificationAlternative,
    ProductExtraction,
    TariffClassificationProposal,
    TariffItem,
)
from app.integrations.llm.base import TariffClassifier, VisionExtractor
from app.services.storage.base import FileStorage


def build_extraction(**overrides: object) -> ProductExtraction:
    """A realistic extraction for a pair of bluetooth headphones."""
    defaults = {
        "name": "Audífonos inalámbricos",
        "brand": None,
        "model": None,
        "material": "Plástico",
        "function": "Reproducir audio de forma inalámbrica sobre las orejas",
        "technical_specs": ["Conexión Bluetooth", "Diadema ajustable", "Batería recargable"],
        "visible_text": None,
        "search_keywords": ["audífonos", "auriculares", "inalámbricos", "bluetooth"],
    }
    defaults.update(overrides)
    return ProductExtraction(**defaults)  # type: ignore[arg-type]


class StubVisionExtractor(VisionExtractor):
    """Returns a fixed extraction, or raises a configured failure."""

    def __init__(
        self,
        extraction: ProductExtraction | None = None,
        error: LlmError | None = None,
    ) -> None:
        self.extraction = extraction or build_extraction()
        self.error = error
        self.calls: list[tuple[int, str]] = []

    async def extract(self, image: bytes, media_type: str) -> ProductExtraction:
        self.calls.append((len(image), media_type))
        if self.error is not None:
            raise self.error
        return self.extraction


class StubTariffClassifier(TariffClassifier):
    """Returns a proposal built from the first candidate, or a failure."""

    def __init__(
        self,
        confidence: float = 0.92,
        error: LlmError | None = None,
        tariff_code: str | None = None,
    ) -> None:
        self.confidence = confidence
        self.error = error
        self.tariff_code = tariff_code
        self.received_candidates: list[TariffItem] = []

    async def classify(
        self,
        extraction: ProductExtraction,
        candidates: list[TariffItem],
    ) -> TariffClassificationProposal:
        self.received_candidates = candidates
        if self.error is not None:
            raise self.error

        chosen = candidates[0]
        alternatives = [
            ClassificationAlternative(
                tariff_code=other.tariff_code,
                nico=other.nico,
                reason="Descripción menos específica para esta mercancía.",
            )
            for other in candidates[1:3]
        ]
        return TariffClassificationProposal(
            tariff_code=self.tariff_code or chosen.tariff_code,
            nico=chosen.nico,
            confidence=self.confidence,
            rationale=(
                "Aplicando la Regla General 1, el texto de la partida describe "
                "la mercancía; por la Regla General 6 se compara al mismo nivel "
                "de subpartida."
            ),
            alternatives=alternatives,
        )


class InMemoryFileStorage(FileStorage):
    """Keeps files in a dictionary keyed by their synthetic path."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def save(self, folder: str, filename: str, content: bytes) -> str:
        path = f"/{folder}/{filename}"
        self.files[path] = content
        return path

    def load(self, path: str) -> bytes:
        try:
            return self.files[path]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc

    def exists(self, path: str) -> bool:
        return path in self.files
