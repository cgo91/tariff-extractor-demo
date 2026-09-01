"""Operation lifecycle use cases (RF-03, RF-10)."""

from __future__ import annotations

import logging
import uuid

from app.domain.enums import OperationStatus
from app.domain.errors import InvalidStateTransitionError, NotFoundError
from app.domain.models import Operation, ProductExtraction, User
from app.repositories.base import OperationRepository
from app.services.image_processing import ImageProcessor
from app.services.storage.base import FileStorage
from app.services.storage.local_storage import UPLOADS

logger = logging.getLogger(__name__)


class OperationService:
    """Creates operations from an upload and reads them back.

    The per-step services (extraction, classification, pedimento) depend on this
    one for loading and ownership checks, so that rule lives in a single place.
    """

    def __init__(
        self,
        operation_repository: OperationRepository,
        file_storage: FileStorage,
        image_processor: ImageProcessor,
    ) -> None:
        self._operations = operation_repository
        self._storage = file_storage
        self._images = image_processor

    async def create(
        self, user: User, content: bytes, declared_media_type: str | None = None
    ) -> Operation:
        """Validate the photo, store it, and open a new operation.

        Raises:
            ValidationError: when the upload is not an acceptable image.
        """
        processed = self._images.process(content, declared_media_type)

        # The filename is generated, never taken from the client.
        filename = f"{uuid.uuid4().hex}.{processed.extension}"
        image_path = self._storage.save(UPLOADS, filename, processed.content)

        operation = await self._operations.insert(
            Operation(
                user_id=str(user.id),
                status=OperationStatus.CREATED,
                image_path=image_path,
            )
        )
        logger.info(
            "Operación %s creada (%dx%d, %s%s)",
            operation.id,
            processed.width,
            processed.height,
            processed.media_type,
            ", convertida" if processed.was_converted else "",
        )
        return operation

    async def get_for_user(self, operation_id: str, user: User) -> Operation:
        """Load an operation owned by the caller.

        Raises:
            NotFoundError: when it does not exist or belongs to someone else.
                Both cases return the same error so the endpoint cannot be used
                to probe for other users' identifiers.
        """
        operation = await self._operations.get_by_id(operation_id)
        if operation is None or operation.user_id != str(user.id):
            raise NotFoundError(f"No existe la operación {operation_id}")
        return operation

    async def list_for_user(self, user: User, limit: int = 50) -> list[Operation]:
        """Return the caller's operations, newest first."""
        return await self._operations.list_by_user(str(user.id), limit)

    async def read_image(self, operation: Operation) -> bytes:
        """Load the stored photograph of an operation.

        Raises:
            NotFoundError: when the file is missing from storage.
        """
        try:
            return self._storage.load(operation.image_path)
        except FileNotFoundError as exc:
            raise NotFoundError(
                "La imagen de la operación ya no está disponible en el servidor."
            ) from exc

    async def update_extraction(
        self, operation: Operation, extraction: ProductExtraction
    ) -> Operation:
        """Persist user edits to the extracted features (RF-04).

        Raises:
            InvalidStateTransitionError: before an extraction exists, or once
                the pedimento has been generated.
        """
        if operation.extraction is None:
            raise InvalidStateTransitionError(
                "Primero hay que extraer las características de la fotografía."
            )
        self._reject_if_closed(operation)

        operation.extraction = extraction
        return await self._operations.update(operation)

    @staticmethod
    def _reject_if_closed(operation: Operation) -> None:
        """Block edits to an operation whose pedimento already exists."""
        if operation.status is OperationStatus.PEDIMENTO_GENERATED:
            raise InvalidStateTransitionError(
                "La operación ya tiene un pedimento generado y no puede modificarse."
            )
