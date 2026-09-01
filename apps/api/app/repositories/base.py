"""Repository abstractions.

Services depend exclusively on these interfaces. Two families of
implementations exist: ``app.repositories.mongo`` for production and
``app.repositories.memory`` for tests. Adding a third storage backend never
requires touching a service.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from pydantic import BaseModel

from app.domain.models import Operation, TariffItem, User


class Repository[TEntity: BaseModel](ABC):
    """Minimal persistence contract shared by every aggregate repository."""

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> TEntity | None:
        """Return the entity with the given id, or None when absent."""

    @abstractmethod
    async def insert(self, entity: TEntity) -> TEntity:
        """Persist a new entity and return it with its assigned id."""


class UserRepository(Repository[User]):
    """Persistence contract for application users."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Return the user registered with the given email, if any."""

    @abstractmethod
    async def upsert_by_email(self, user: User) -> User:
        """Create the user, or update the password hash when it already exists.

        Used by the seed script so that re-running it stays idempotent.
        """


class TariffItemRepository(ABC):
    """Read-mostly contract for the TIGIE catalog.

    Tariff items are identified by their natural key (``tariff_code`` +
    ``nico``) rather than by a surrogate id, so this repository deliberately
    does not extend ``Repository``.
    """

    @abstractmethod
    async def ensure_indexes(self) -> None:
        """Create the text and uniqueness indexes the catalog relies on."""

    @abstractmethod
    async def replace_all(self, items: Iterable[TariffItem]) -> int:
        """Replace the whole catalog and return the number of stored items."""

    @abstractmethod
    async def count(self) -> int:
        """Return how many tariff items are stored."""

    @abstractmethod
    async def search_by_text(self, query: str, limit: int = 15) -> list[TariffItem]:
        """Return the most relevant tariff items for a free-text query."""

    @abstractmethod
    async def get_by_code(self, tariff_code: str, nico: str | None = None) -> TariffItem | None:
        """Return one tariff item by its natural key."""

    @abstractmethod
    async def find_by_codes(self, tariff_codes: Iterable[str]) -> list[TariffItem]:
        """Return every tariff item whose code is in the given collection."""


class OperationRepository(Repository[Operation]):
    """Persistence contract for import operations."""

    @abstractmethod
    async def update(self, operation: Operation) -> Operation:
        """Persist the full state of an existing operation."""

    @abstractmethod
    async def list_by_user(self, user_id: str, limit: int = 50) -> list[Operation]:
        """Return the user's operations, newest first."""
