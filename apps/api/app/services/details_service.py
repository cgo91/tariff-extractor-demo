"""Operation data capture and settlement (RF-07, RF-08)."""

from __future__ import annotations

import logging

from app.domain.enums import OperationStatus
from app.domain.errors import InvalidStateTransitionError
from app.domain.models import Operation, OperationDetails
from app.repositories.base import OperationRepository
from app.services.catalog_service import CatalogService
from app.services.duty_calculator import DutyCalculator

logger = logging.getLogger(__name__)


class OperationDetailsService:
    """Saves the commercial data and settles the contributions.

    The two steps live together because the settlement is a pure consequence of
    the data: saving details without recomputing it would leave the operation
    holding amounts that no longer match its own numbers.
    """

    def __init__(
        self,
        operation_repository: OperationRepository,
        catalog_service: CatalogService,
        duty_calculator: DutyCalculator,
    ) -> None:
        self._operations = operation_repository
        self._catalog = catalog_service
        self._calculator = duty_calculator

    async def save(self, operation: Operation, details: OperationDetails) -> Operation:
        """Persist the operation data and the resulting settlement.

        Raises:
            InvalidStateTransitionError: without a classification, or once the
                pedimento has been generated.
            NotFoundError: when the classified code is no longer in the catalog.
        """
        if operation.classification is None:
            raise InvalidStateTransitionError(
                "Primero hay que clasificar la mercancía."
            )
        if operation.status is OperationStatus.PEDIMENTO_GENERATED:
            raise InvalidStateTransitionError(
                "La operación ya tiene un pedimento generado y no puede modificarse."
            )

        # The IGI rate comes from the catalog, never from the request: the
        # amount owed is not something the client gets to state.
        tariff_item = await self._catalog.get_item(
            operation.classification.tariff_code, operation.classification.nico
        )

        operation.operation_details = details
        operation.settlement = self._calculator.calculate(
            invoice_value_usd=details.invoice_value_usd,
            exchange_rate=details.exchange_rate,
            igi_rate=tariff_item.igi_rate,
        )
        operation.error_message = None

        logger.info(
            "Operación %s liquidada: valor aduana %.2f, total %.2f",
            operation.id,
            operation.settlement.customs_value,
            operation.settlement.total,
        )
        return await self._operations.update(operation)
