"""Tariff classification use case (RF-05).

Two steps, as the PRD describes them: search the catalog for candidates using
the keywords Claude generated, then ask Claude to choose among them. The
candidate list is what keeps the model inside the catalog we actually hold.
"""

from __future__ import annotations

import logging

from app.domain.enums import OperationStatus
from app.domain.errors import DomainError, InvalidStateTransitionError, LlmError
from app.domain.models import Operation, ProductExtraction, TariffClassification, TariffItem
from app.integrations.llm.base import TariffClassifier
from app.repositories.base import OperationRepository
from app.services.catalog_service import MAX_SEARCH_RESULTS, CatalogService

logger = logging.getLogger(__name__)


class ClassificationService:
    """Proposes a tariff code for an extracted operation."""

    def __init__(
        self,
        operation_repository: OperationRepository,
        catalog_service: CatalogService,
        classifier: TariffClassifier,
        confidence_threshold: float,
    ) -> None:
        self._operations = operation_repository
        self._catalog = catalog_service
        self._classifier = classifier
        self._confidence_threshold = confidence_threshold

    async def classify(self, operation: Operation) -> Operation:
        """Find candidates, classify, and persist both on the operation.

        Re-running is allowed and discards any previous confirmation: a fresh
        proposal has not been reviewed by anyone.

        Raises:
            InvalidStateTransitionError: without an extraction, or once the
                pedimento has been generated.
            LlmError: when Claude fails or leaves the candidate list; the
                failure is persisted on the operation first.
        """
        if operation.status is OperationStatus.PEDIMENTO_GENERATED:
            raise InvalidStateTransitionError(
                "La operación ya tiene un pedimento generado y no puede reclasificarse."
            )
        if operation.extraction is None:
            raise InvalidStateTransitionError(
                "Primero hay que extraer las características de la fotografía."
            )

        candidates = await self._find_candidates(operation.extraction)
        if not candidates:
            return await self._record_failure(
                operation,
                LlmError(
                    "El catálogo no tiene fracciones que coincidan con esta mercancía. "
                    "Edita el nombre o la función y vuelve a intentarlo."
                ),
            )

        try:
            proposal = await self._classifier.classify(operation.extraction, candidates)
        except LlmError as error:
            operation.candidates = candidates
            return await self._record_failure(operation, error)

        operation.candidates = candidates
        operation.classification = TariffClassification(
            **proposal.model_dump(), confirmed_by_user=False
        )
        operation.status = OperationStatus.CLASSIFIED
        operation.error_message = None

        logger.info(
            "Operación %s clasificada como %s (confianza %.2f%s)",
            operation.id,
            proposal.tariff_code,
            proposal.confidence,
            ", requiere revisión" if proposal.confidence < self._confidence_threshold else "",
        )
        return await self._operations.update(operation)

    async def _find_candidates(self, extraction: ProductExtraction) -> list[TariffItem]:
        """Search the catalog with the model's keywords plus the product name.

        The name is appended last so that the generated keywords, which are
        written specifically for catalog matching, drive the ranking.
        """
        queries = [*extraction.search_keywords, extraction.name]
        candidates = await self._catalog.find_candidates(queries, MAX_SEARCH_RESULTS)
        logger.debug("Candidatos encontrados: %d", len(candidates))
        return candidates

    async def _record_failure(self, operation: Operation, error: DomainError) -> Operation:
        """Persist the failure on the aggregate, then re-raise it."""
        operation.status = OperationStatus.ERROR
        operation.error_message = error.message
        await self._operations.update(operation)
        logger.warning(
            "Clasificación fallida en la operación %s: %s", operation.id, error.message
        )
        raise error
