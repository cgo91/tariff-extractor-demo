"""MongoDB implementation of :class:`OperationRepository`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymongo import DESCENDING

from app.domain.models import Operation, utc_now
from app.repositories.base import OperationRepository
from app.repositories.mongo.base import to_object_id, with_string_id

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pymongo.asynchronous.database import AsyncDatabase

COLLECTION_NAME = "operations"


class MongoOperationRepository(OperationRepository):
    """Stores import operations in the ``operations`` collection."""

    def __init__(self, database: AsyncDatabase) -> None:
        self._collection = database[COLLECTION_NAME]

    async def get_by_id(self, entity_id: str) -> Operation | None:
        object_id = to_object_id(entity_id)
        if object_id is None:
            return None
        document = await self._collection.find_one({"_id": object_id})
        return Operation(**with_string_id(document)) if document else None

    async def insert(self, entity: Operation) -> Operation:
        document = entity.model_dump(exclude={"id"})
        result = await self._collection.insert_one(document)
        return entity.model_copy(update={"id": str(result.inserted_id)})

    async def update(self, operation: Operation) -> Operation:
        """Persist the whole aggregate and refresh ``updated_at``."""
        if operation.id is None:
            raise ValueError("Cannot update an operation without an id")
        object_id = to_object_id(operation.id)
        if object_id is None:
            raise ValueError(f"Malformed operation id: {operation.id}")

        updated = operation.model_copy(update={"updated_at": utc_now()})
        await self._collection.replace_one(
            {"_id": object_id}, updated.model_dump(exclude={"id"})
        )
        return updated

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[Operation]:
        cursor = (
            self._collection.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return [Operation(**with_string_id(doc)) async for doc in cursor]
