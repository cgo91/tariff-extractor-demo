"""File storage abstraction.

Services never touch the filesystem directly. Swapping local disk for object
storage means adding one subclass, not editing a service.
"""

from abc import ABC, abstractmethod


class FileStorage(ABC):
    """Stores and retrieves the binary artifacts of an operation."""

    @abstractmethod
    def save(self, folder: str, filename: str, content: bytes) -> str:
        """Write the content and return the path used to read it back."""

    @abstractmethod
    def load(self, path: str) -> bytes:
        """Read a previously stored file.

        Raises:
            FileNotFoundError: when the path does not exist.
        """

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Return True when the path points at a readable file."""
