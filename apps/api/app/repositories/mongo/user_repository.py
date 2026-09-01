"""MongoDB implementation of :class:`UserRepository`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import User
from app.repositories.base import UserRepository
from app.repositories.mongo.base import to_object_id, with_string_id

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pymongo.asynchronous.database import AsyncDatabase

COLLECTION_NAME = "users"


class MongoUserRepository(UserRepository):
    """Stores users in the ``users`` collection."""

    def __init__(self, database: AsyncDatabase) -> None:
        self._collection = database[COLLECTION_NAME]

    async def get_by_id(self, entity_id: str) -> User | None:
        object_id = to_object_id(entity_id)
        if object_id is None:
            return None
        document = await self._collection.find_one({"_id": object_id})
        return User(**with_string_id(document)) if document else None

    async def get_by_email(self, email: str) -> User | None:
        document = await self._collection.find_one({"email": email.lower()})
        return User(**with_string_id(document)) if document else None

    async def insert(self, entity: User) -> User:
        document = entity.model_dump(exclude={"id"})
        document["email"] = document["email"].lower()
        result = await self._collection.insert_one(document)
        return entity.model_copy(update={"id": str(result.inserted_id)})

    async def upsert_by_email(self, user: User) -> User:
        """Idempotent create-or-update, used by the seed script."""
        email = user.email.lower()
        existing = await self._collection.find_one({"email": email})
        if existing is None:
            return await self.insert(user)
        await self._collection.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": user.password_hash}},
        )
        return user.model_copy(update={"id": str(existing["_id"]), "email": email})
