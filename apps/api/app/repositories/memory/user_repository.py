"""In-memory :class:`UserRepository`, used by the test suite."""

from __future__ import annotations

from itertools import count

from app.domain.models import User
from app.repositories.base import UserRepository


class InMemoryUserRepository(UserRepository):
    """Dictionary-backed user store with the same contract as the Mongo one."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._ids = count(1)

    async def get_by_id(self, entity_id: str) -> User | None:
        return self._users.get(entity_id)

    async def get_by_email(self, email: str) -> User | None:
        target = email.lower()
        return next((u for u in self._users.values() if u.email.lower() == target), None)

    async def insert(self, entity: User) -> User:
        new_id = str(next(self._ids))
        stored = entity.model_copy(update={"id": new_id, "email": entity.email.lower()})
        self._users[new_id] = stored
        return stored

    async def upsert_by_email(self, user: User) -> User:
        existing = await self.get_by_email(user.email)
        if existing is None:
            return await self.insert(user)
        updated = existing.model_copy(update={"password_hash": user.password_hash})
        self._users[str(existing.id)] = updated
        return updated
