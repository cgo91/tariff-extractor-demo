"""Upload validation and normalisation (RF-03).

Kept separate from the operation service because it is pure computation over
bytes: no database, no storage, no network. That makes the size and format
rules straightforward to test.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.domain.errors import ValidationError

logger = logging.getLogger(__name__)

# Formats the API accepts from the browser.
JPEG_MEDIA_TYPE = "image/jpeg"
PNG_MEDIA_TYPE = "image/png"
ACCEPTED_MEDIA_TYPES = {JPEG_MEDIA_TYPE, PNG_MEDIA_TYPE}

# HEIC arrives from iPhones and is converted to JPEG before anything else
# touches it, because Claude does not accept it.
HEIC_MEDIA_TYPES = {"image/heic", "image/heif"}

# Pillow format name -> media type and file extension.
_FORMAT_MAP = {
    "JPEG": (JPEG_MEDIA_TYPE, "jpg"),
    "PNG": (PNG_MEDIA_TYPE, "png"),
}

# Registering the HEIF opener is optional: if the package is missing the API
# still serves JPEG and PNG, it just rejects HEIC with a clear message.
try:  # pragma: no cover - depends on the runtime environment
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:  # pragma: no cover
    HEIC_SUPPORTED = False
    logger.warning("pillow-heif no está instalado; no se podrán convertir imágenes HEIC")


@dataclass(frozen=True)
class ProcessedImage:
    """An upload that passed validation and is ready to be stored."""

    content: bytes
    media_type: str
    extension: str
    width: int
    height: int
    was_converted: bool


class ImageProcessor:
    """Validates uploads and normalises them to a format Claude accepts."""

    def __init__(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes

    def process(self, content: bytes, declared_media_type: str | None = None) -> ProcessedImage:
        """Validate an upload and return it as JPEG or PNG.

        Args:
            content: Raw bytes as received from the client.
            declared_media_type: The browser's Content-Type, used only to give
                a better error message. The real format is read from the bytes,
                because the header is trivially wrong or spoofed.

        Raises:
            ValidationError: when the file is empty, too large, not an image,
                or in a format the MVP does not accept.
        """
        self._reject_bad_size(content)
        image = self._open(content, declared_media_type)

        try:
            source_format = (image.format or "").upper()
            if source_format in _FORMAT_MAP:
                media_type, extension = _FORMAT_MAP[source_format]
                return ProcessedImage(
                    content=content,
                    media_type=media_type,
                    extension=extension,
                    width=image.width,
                    height=image.height,
                    was_converted=False,
                )

            # Anything else Pillow could open (HEIC in practice) is re-encoded.
            return self._to_jpeg(image)
        finally:
            image.close()

    # --- internals ---------------------------------------------------------

    def _reject_bad_size(self, content: bytes) -> None:
        if not content:
            raise ValidationError("El archivo está vacío.")
        if len(content) > self._max_bytes:
            limit_mb = self._max_bytes / (1024 * 1024)
            actual_mb = len(content) / (1024 * 1024)
            raise ValidationError(
                f"La imagen pesa {actual_mb:.1f} MB y el máximo es {limit_mb:.0f} MB."
            )

    def _open(self, content: bytes, declared_media_type: str | None) -> Image.Image:
        try:
            image = Image.open(io.BytesIO(content))
            image.load()
            return image
        except UnidentifiedImageError as exc:
            if declared_media_type in HEIC_MEDIA_TYPES and not HEIC_SUPPORTED:
                raise ValidationError(
                    "El servidor no puede convertir imágenes HEIC. "
                    "Vuelve a exportarla como JPG o PNG."
                ) from exc
            raise ValidationError(
                "El archivo no es una imagen válida. Se aceptan JPG y PNG."
            ) from exc
        except OSError as exc:
            raise ValidationError("La imagen está dañada o incompleta.") from exc

    def _to_jpeg(self, image: Image.Image) -> ProcessedImage:
        """Re-encode to JPEG, flattening transparency onto white."""
        converted = image.convert("RGB")
        buffer = io.BytesIO()
        converted.save(buffer, format="JPEG", quality=90, optimize=True)
        encoded = buffer.getvalue()

        # Re-encoding can push a borderline file over the limit.
        self._reject_bad_size(encoded)

        return ProcessedImage(
            content=encoded,
            media_type=JPEG_MEDIA_TYPE,
            extension="jpg",
            width=converted.width,
            height=converted.height,
            was_converted=True,
        )
