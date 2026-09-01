"""MongoDB connection lifecycle.

Uses PyMongo's native async client (``AsyncMongoClient``), which supersedes the
deprecated Motor driver while exposing the same coroutine-based API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymongo import AsyncMongoClient

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pymongo.asynchronous.database import AsyncDatabase


class MongoConnection:
    """Owns the single client instance shared by every repository."""

    def __init__(self, uri: str, database_name: str) -> None:
        self._uri = uri
        self._database_name = database_name
        self._client: AsyncMongoClient | None = None

    async def connect(self) -> None:
        """Open the connection and fail fast if the server is unreachable."""
        self._client = AsyncMongoClient(self._uri, serverSelectionTimeoutMS=5000)
        await self._client.admin.command("ping")

    async def close(self) -> None:
        """Release the connection pool."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def database(self) -> AsyncDatabase:
        """Return the application database, connecting lazily if needed."""
        if self._client is None:
            self._client = AsyncMongoClient(self._uri, serverSelectionTimeoutMS=5000)
        return self._client[self._database_name]
