"""LLM integration contracts.

Services depend on these interfaces rather than on the Anthropic SDK, so the
extraction and classification use cases can be tested with deterministic
doubles and no network access.
"""

from abc import ABC, abstractmethod

from app.domain.models import (
    ProductExtraction,
    TariffClassificationProposal,
    TariffItem,
)


class VisionExtractor(ABC):
    """Turns a product photograph into structured features."""

    @abstractmethod
    async def extract(self, image: bytes, media_type: str) -> ProductExtraction:
        """Describe the photographed product.

        Raises:
            LlmError: when the provider fails or returns an unusable payload.
        """


class TariffClassifier(ABC):
    """Chooses a tariff code for an extracted product."""

    @abstractmethod
    async def classify(
        self,
        extraction: ProductExtraction,
        candidates: list[TariffItem],
    ) -> TariffClassificationProposal:
        """Pick one of the candidates and justify the choice.

        Implementations must guarantee the returned code belongs to
        ``candidates``.

        Raises:
            ClassificationOutOfCandidatesError: when the model keeps proposing
                a code outside the candidate list.
            LlmError: for any other provider failure.
        """
