"""Human review of the classification (RF-06).

The product's whole premise is that the system proposes and a person decides,
so this is the step that gives the demo its point: the reviewer can accept the
proposal, switch to one of the alternatives, or pick any code in the catalog.
"""

from __future__ import annotations

import logging

from app.domain.enums import OperationStatus
from app.domain.errors import InvalidStateTransitionError
from app.domain.models import Operation
from app.repositories.base import OperationRepository
from app.services.catalog_service import CatalogService

logger = logging.getLogger(__name__)


class ClassificationReviewService:
    """Confirms or corrects the proposed tariff code."""

    def __init__(
        self,
        operation_repository: OperationRepository,
        catalog_service: CatalogService,
    ) -> None:
        self._operations = operation_repository
        self._catalog = catalog_service

    async def confirm(self, operation: Operation, tariff_code: str, nico: str) -> Operation:
        """Record the reviewer's decision.

        The pair is validated against the catalog rather than trusted, because
        the pedimento later needs the item's IGI rate and unit of measure: a
        code that is not in the catalog would break the settlement.

        When the reviewer picks a different code, the model's original choice is
        preserved in ``original_tariff_code`` so the record still shows what was
        proposed and what a human decided.

        Raises:
            InvalidStateTransitionError: without a classification, or once the
                pedimento has been generated.
            NotFoundError: when the code and NICO are not in the catalog.
        """
        if operation.classification is None:
            raise InvalidStateTransitionError(
                "La operación todavía no tiene una clasificación que revisar."
            )
        if operation.status is OperationStatus.PEDIMENTO_GENERATED:
            raise InvalidStateTransitionError(
                "La operación ya tiene un pedimento generado y no puede modificarse."
            )

        # Raises NotFoundError when the pair does not exist.
        await self._catalog.get_item(tariff_code, nico)

        classification = operation.classification
        original = classification.original_tariff_code or classification.tariff_code

        operation.classification = classification.model_copy(
            update={
                "tariff_code": tariff_code,
                "nico": nico,
                "confirmed_by_user": True,
                "original_tariff_code": original,
            }
        )

        # Confirming after a failed step also clears the error banner.
        operation.status = OperationStatus.CLASSIFIED
        operation.error_message = None

        # The settlement was computed from the previous code's IGI rate, so it
        # no longer describes this operation.
        if operation.classification.was_overridden:
            operation.settlement = None
            logger.info(
                "Operación %s: el usuario cambió %s por %s",
                operation.id,
                original,
                tariff_code,
            )
        else:
            logger.info("Operación %s: el usuario confirmó %s", operation.id, tariff_code)

        return await self._operations.update(operation)
