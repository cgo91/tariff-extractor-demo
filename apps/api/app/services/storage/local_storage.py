"""Local filesystem implementation of :class:`FileStorage`."""

from __future__ import annotations

from pathlib import Path

from app.services.storage.base import FileStorage

# Logical folder names, mapped to real directories by the constructor.
UPLOADS = "uploads"
PEDIMENTOS = "pedimentos"


class LocalFileStorage(FileStorage):
    """Writes uploads and generated PDFs to directories on disk."""

    def __init__(self, upload_dir: Path, pedimento_dir: Path) -> None:
        self._directories = {UPLOADS: Path(upload_dir), PEDIMENTOS: Path(pedimento_dir)}
        for directory in self._directories.values():
            directory.mkdir(parents=True, exist_ok=True)

    def save(self, folder: str, filename: str, content: bytes) -> str:
        directory = self._resolve_directory(folder)
        # Only the basename is honoured: a caller-supplied name must never be
        # able to escape the storage directory.
        target = directory / Path(filename).name
        target.write_bytes(content)
        return str(target)

    def load(self, path: str) -> bytes:
        target = Path(path)
        if not target.is_file():
            raise FileNotFoundError(f"No existe el archivo {path}")
        return target.read_bytes()

    def exists(self, path: str) -> bool:
        return Path(path).is_file()

    def _resolve_directory(self, folder: str) -> Path:
        try:
            return self._directories[folder]
        except KeyError as exc:
            raise ValueError(f"Carpeta de almacenamiento desconocida: {folder}") from exc
