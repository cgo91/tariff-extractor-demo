"""Enumerations shared across the domain."""

from enum import StrEnum


class OperationStatus(StrEnum):
    """Lifecycle of an import operation.

    The happy path runs CREATED -> EXTRACTED -> CLASSIFIED -> PEDIMENTO_GENERATED.
    ERROR is terminal only until the user retries the failed step.
    """

    CREATED = "created"
    EXTRACTED = "extracted"
    CLASSIFIED = "classified"
    PEDIMENTO_GENERATED = "pedimento_generated"
    ERROR = "error"

    @property
    def rank(self) -> int:
        """Return the progress index used to compare statuses.

        ERROR is intentionally ranked below every successful status so that a
        retry can move the operation forward again.
        """
        order = {
            OperationStatus.ERROR: -1,
            OperationStatus.CREATED: 0,
            OperationStatus.EXTRACTED: 1,
            OperationStatus.CLASSIFIED: 2,
            OperationStatus.PEDIMENTO_GENERATED: 3,
        }
        return order[self]
