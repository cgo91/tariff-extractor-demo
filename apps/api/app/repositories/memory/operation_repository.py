"""In-memory :class:`OperationRepository`, used by the test suite."""

from __future__ import annotations

from itertools import count

from app.domain.models import Operation, utc_now
from app.repositories.base import OperationRepository


class InMemoryOperationRepository(OperationRepository):
    """Dictionary-backed operation store with the same contract as Mongo's."""

    def __init__(self) -> None:
        self._operations: dict[str, Operation] = {}
        self._ids = count(1)

    async def get_by_id(self, entity_id: str) -> Operation | None:
        return self._operations.get(entity_id)

    async def insert(self, entity: Operation) -> Operation:
        new_id = str(next(self._ids))
        stored = entity.model_copy(update={"id": new_id})
        self._operations[new_id] = stored
        return stored

    async def update(self, operation: Operation) -> Operation:
        if operation.id is None:
            raise ValueError("Cannot update an operation without an id")
        updated = operation.model_copy(update={"updated_at": utc_now()})
        self._operations[operation.id] = updated
        return updated

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[Operation]:
        matches = [op for op in self._operations.values() if op.user_id == user_id]
        matches.sort(key=lambda op: op.created_at, reverse=True)
        return matches[:limit]
