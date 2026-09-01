"""Feature extraction use case (RF-04)."""

from __future__ import annotations

import logging

from app.domain.enums import OperationStatus
from app.domain.errors import DomainError, InvalidStateTransitionError, LlmError
from app.domain.models import Operation
from app.integrations.llm.base import VisionExtractor
from app.repositories.base import OperationRepository
from app.services.operation_service import OperationService

logger = logging.getLogger(__name__)


class ExtractionService:
    """Runs Claude vision over the stored photograph and records the result.

    A provider failure is not allowed to leave the operation in limbo: it is
    written to the aggregate as ``status = error`` with the message, which is
    what lets the UI offer a retry (see the non-functional requirements).
    """

    def __init__(
        self,
        operation_service: OperationService,
        operation_repository: OperationRepository,
        extractor: VisionExtractor,
    ) -> None:
        self._operations_service = operation_service
        self._operations = operation_repository
        self._extractor = extractor

    async def extract(self, operation: Operation) -> Operation:
        """Extract the product features and advance the operation.

        Re-running on an already extracted operation is allowed: that is the
        retry path after a failure or a poor result.

        Raises:
            InvalidStateTransitionError: once the pedimento has been generated.
            LlmError: when Claude fails; the failure is persisted first.
        """
        if operation.status is OperationStatus.PEDIMENTO_GENERATED:
            raise InvalidStateTransitionError(
                "La operación ya tiene un pedimento generado y no puede reprocesarse."
            )

        image = await self._operations_service.read_image(operation)
        media_type = _media_type_for(operation.image_path)

        try:
            extraction = await self._extractor.extract(image, media_type)
        except LlmError as error:
            return await self._record_failure(operation, error)

        operation.extraction = extraction
        operation.status = OperationStatus.EXTRACTED
        operation.error_message = None
        logger.info("Operación %s extraída: %s", operation.id, extraction.name)
        return await self._operations.update(operation)

    async def _record_failure(self, operation: Operation, error: DomainError) -> Operation:
        """Persist the failure on the aggregate, then re-raise it."""
        operation.status = OperationStatus.ERROR
        operation.error_message = error.message
        await self._operations.update(operation)
        logger.warning("Extracción fallida en la operación %s: %s", operation.id, error.message)
        raise error


def _media_type_for(image_path: str) -> str:
    """Infer the media type from the stored file's extension.

    Safe because the extension is assigned by ``ImageProcessor`` after reading
    the actual bytes, never taken from the client.
    """
    return "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
