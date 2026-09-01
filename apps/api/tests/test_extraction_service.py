"""Tests for the operation and extraction use cases (RF-03, RF-04)."""

from __future__ import annotations

import pytest

from app.domain.enums import OperationStatus
from app.domain.errors import InvalidStateTransitionError, LlmError, NotFoundError
from app.domain.models import User
from app.services.extraction_service import ExtractionService
from app.services.operation_service import OperationService
from tests.doubles import InMemoryFileStorage, StubVisionExtractor, build_extraction


class TestOperationCreation:
    async def test_stores_the_image_and_opens_the_operation(
        self,
        operation_service: OperationService,
        file_storage: InMemoryFileStorage,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")

        assert operation.id is not None
        assert operation.status is OperationStatus.CREATED
        assert operation.user_id == "user-1"
        assert file_storage.load(operation.image_path) == jpeg_bytes

    async def test_never_reuses_the_client_filename(
        self,
        operation_service: OperationService,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        """Paths are generated, so two uploads cannot collide or traverse."""
        first = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")
        second = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")

        assert first.image_path != second.image_path
        assert ".." not in first.image_path

    async def test_converted_uploads_are_stored_as_jpeg(
        self,
        operation_service: OperationService,
        demo_user: User,
        png_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, png_bytes, "image/png")

        assert operation.image_path.endswith(".png")


class TestOwnership:
    async def test_hides_operations_of_other_users(
        self,
        operation_service: OperationService,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")
        intruder = User(id="user-2", email="otro@aduana.mx", password_hash="unused")

        with pytest.raises(NotFoundError):
            await operation_service.get_for_user(str(operation.id), intruder)

    async def test_unknown_id_is_not_found(
        self, operation_service: OperationService, demo_user: User
    ) -> None:
        with pytest.raises(NotFoundError):
            await operation_service.get_for_user("does-not-exist", demo_user)


class TestExtraction:
    async def test_records_the_features_and_advances_the_status(
        self,
        operation_service: OperationService,
        extraction_service: ExtractionService,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")

        extracted = await extraction_service.extract(operation)

        assert extracted.status is OperationStatus.EXTRACTED
        assert extracted.extraction is not None
        assert extracted.extraction.name == "Audífonos inalámbricos"
        assert extracted.error_message is None

    async def test_sends_the_stored_image_with_its_media_type(
        self,
        operation_service: OperationService,
        extraction_service: ExtractionService,
        vision_extractor: StubVisionExtractor,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")

        await extraction_service.extract(operation)

        assert vision_extractor.calls == [(len(jpeg_bytes), "image/jpeg")]

    async def test_png_operations_report_the_png_media_type(
        self,
        operation_service: OperationService,
        extraction_service: ExtractionService,
        vision_extractor: StubVisionExtractor,
        demo_user: User,
        png_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, png_bytes, "image/png")

        await extraction_service.extract(operation)

        assert vision_extractor.calls[0][1] == "image/png"


class TestExtractionFailure:
    async def test_persists_the_failure_before_raising(
        self,
        operation_service: OperationService,
        operation_repository,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        """The UI can only offer a retry if the error survives the request."""
        failing = StubVisionExtractor(error=LlmError("Claude no está disponible."))
        service = ExtractionService(operation_service, operation_repository, failing)
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")

        with pytest.raises(LlmError):
            await service.extract(operation)

        stored = await operation_repository.get_by_id(str(operation.id))
        assert stored.status is OperationStatus.ERROR
        assert stored.error_message == "Claude no está disponible."

    async def test_a_retry_clears_the_previous_error(
        self,
        operation_service: OperationService,
        extraction_service: ExtractionService,
        operation_repository,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")
        operation.status = OperationStatus.ERROR
        operation.error_message = "fallo anterior"
        await operation_repository.update(operation)

        retried = await extraction_service.extract(operation)

        assert retried.status is OperationStatus.EXTRACTED
        assert retried.error_message is None

    async def test_rejects_reprocessing_a_finished_operation(
        self,
        operation_service: OperationService,
        extraction_service: ExtractionService,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")
        operation.status = OperationStatus.PEDIMENTO_GENERATED

        with pytest.raises(InvalidStateTransitionError):
            await extraction_service.extract(operation)

    async def test_reports_a_missing_image_file(
        self,
        operation_service: OperationService,
        extraction_service: ExtractionService,
        file_storage: InMemoryFileStorage,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")
        file_storage.files.clear()

        with pytest.raises(NotFoundError):
            await extraction_service.extract(operation)


class TestExtractionEditing:
    async def test_applies_the_user_corrections(
        self,
        operation_service: OperationService,
        extraction_service: ExtractionService,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")
        extracted = await extraction_service.extract(operation)

        edited = await operation_service.update_extraction(
            extracted,
            build_extraction(name="Audífonos de diadema", function="Escuchar audio"),
        )

        assert edited.extraction is not None
        assert edited.extraction.name == "Audífonos de diadema"
        assert edited.extraction.function == "Escuchar audio"

    async def test_rejects_editing_before_extracting(
        self,
        operation_service: OperationService,
        demo_user: User,
        jpeg_bytes: bytes,
    ) -> None:
        operation = await operation_service.create(demo_user, jpeg_bytes, "image/jpeg")

        with pytest.raises(InvalidStateTransitionError):
            await operation_service.update_extraction(operation, build_extraction())
