"""Catalog source abstraction.

The seed script does not care where tariff items come from. Adding a new origin
(a REST feed, a different spreadsheet layout) means adding one subclass here.
"""

from abc import ABC, abstractmethod

from app.domain.models import TariffItem


class CatalogSource(ABC):
    """Produces the list of tariff items to load into MongoDB."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human readable identifier, printed by the seed script."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when this source has everything it needs to run."""

    @abstractmethod
    def load(self) -> list[TariffItem]:
        """Read, normalise and validate the tariff items."""
