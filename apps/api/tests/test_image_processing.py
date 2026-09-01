"""Tests for upload validation and normalisation (RF-03)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.domain.errors import ValidationError
from app.services.image_processing import (
    JPEG_MEDIA_TYPE,
    PNG_MEDIA_TYPE,
    ImageProcessor,
)


class TestAcceptedFormats:
    def test_keeps_a_jpeg_untouched(
        self, image_processor: ImageProcessor, jpeg_bytes: bytes
    ) -> None:
        result = image_processor.process(jpeg_bytes, "image/jpeg")

        assert result.media_type == JPEG_MEDIA_TYPE
        assert result.extension == "jpg"
        assert result.content == jpeg_bytes
        assert not result.was_converted
        assert (result.width, result.height) == (48, 32)

    def test_keeps_a_png_untouched(
        self, image_processor: ImageProcessor, png_bytes: bytes
    ) -> None:
        result = image_processor.process(png_bytes, "image/png")

        assert result.media_type == PNG_MEDIA_TYPE
        assert result.extension == "png"
        assert not result.was_converted

    def test_trusts_the_bytes_over_the_declared_type(
        self, image_processor: ImageProcessor, jpeg_bytes: bytes
    ) -> None:
        """A wrong Content-Type must not change how the file is stored."""
        result = image_processor.process(jpeg_bytes, "image/png")

        assert result.media_type == JPEG_MEDIA_TYPE


class TestConversion:
    def test_converts_an_unsupported_but_readable_format_to_jpeg(
        self, image_processor: ImageProcessor
    ) -> None:
        """Stands in for HEIC, which follows the same re-encoding path."""
        buffer = io.BytesIO()
        Image.new("RGB", (20, 20), color=(30, 90, 60)).save(buffer, format="BMP")

        result = image_processor.process(buffer.getvalue(), "image/bmp")

        assert result.media_type == JPEG_MEDIA_TYPE
        assert result.extension == "jpg"
        assert result.was_converted
        assert result.content.startswith(b"\xff\xd8")  # JPEG magic number

    def test_flattens_transparency_when_converting(
        self, image_processor: ImageProcessor
    ) -> None:
        buffer = io.BytesIO()
        Image.new("RGBA", (16, 16), color=(0, 0, 0, 0)).save(buffer, format="TIFF")

        result = image_processor.process(buffer.getvalue(), "image/tiff")

        assert result.was_converted
        reopened = Image.open(io.BytesIO(result.content))
        assert reopened.mode == "RGB"


class TestRejection:
    def test_rejects_an_empty_file(self, image_processor: ImageProcessor) -> None:
        with pytest.raises(ValidationError, match="vacío"):
            image_processor.process(b"", "image/jpeg")

    def test_rejects_a_file_over_the_limit(self, jpeg_bytes: bytes) -> None:
        processor = ImageProcessor(max_bytes=len(jpeg_bytes) - 1)

        with pytest.raises(ValidationError, match="máximo"):
            processor.process(jpeg_bytes, "image/jpeg")

    def test_rejects_a_file_that_is_not_an_image(
        self, image_processor: ImageProcessor
    ) -> None:
        with pytest.raises(ValidationError, match="no es una imagen"):
            image_processor.process(b"esto es un PDF, no una foto", "application/pdf")

    def test_rejects_a_truncated_image(
        self, image_processor: ImageProcessor, png_bytes: bytes
    ) -> None:
        with pytest.raises(ValidationError):
            image_processor.process(png_bytes[: len(png_bytes) // 2], "image/png")
