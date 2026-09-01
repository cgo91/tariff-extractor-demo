"""Tests for the two-step classification use case (RF-05)."""

from __future__ import annotations

import pytest

from app.domain.enums import OperationStatus
from app.domain.errors import InvalidStateTransitionError, LlmError
from app.domain.models import Operation, TariffItem
from app.services.catalog_service import MAX_SEARCH_RESULTS, CatalogService
from app.services.classification_service import ClassificationService
from tests.conftest import CONFIDENCE_THRESHOLD
from tests.doubles import StubTariffClassifier, build_extraction


def make_extracted_operation(**extraction_overrides: object) -> Operation:
    """An operation sitting exactly where classification begins."""
    return Operation(
        id=None,
        user_id="user-1",
        status=OperationStatus.EXTRACTED,
        image_path="/uploads/photo.jpg",
        extraction=build_extraction(**extraction_overrides),
    )


class TestCandidateSearch:
    async def test_passes_catalog_candidates_to_the_classifier(
        self,
        classification_service: ClassificationService,
        tariff_classifier: StubTariffClassifier,
        operation_repository,
    ) -> None:
        operation = await operation_repository.insert(make_extracted_operation())

        await classification_service.classify(operation)

        assert tariff_classifier.received_candidates
        assert all(
            isinstance(candidate, TariffItem)
            for candidate in tariff_classifier.received_candidates
        )

    async def test_headphone_keywords_surface_heading_8518(
        self,
        classification_service: ClassificationService,
        tariff_classifier: StubTariffClassifier,
        operation_repository,
    ) -> None:
        operation = await operation_repository.insert(make_extracted_operation())

        await classification_service.classify(operation)

        codes = [item.tariff_code for item in tariff_classifier.received_candidates]
        assert any(code.startswith("8518") for code in codes)

    async def test_never_exceeds_the_candidate_cap(
        self,
        classification_service: ClassificationService,
        tariff_classifier: StubTariffClassifier,
        operation_repository,
    ) -> None:
        operation = await operation_repository.insert(
            make_extracted_operation(
                search_keywords=["eléctricos", "aparatos", "datos", "cables", "unidades"]
            )
        )

        await classification_service.classify(operation)

        assert len(tariff_classifier.received_candidates) <= MAX_SEARCH_RESULTS

    async def test_persists_the_candidates_on_the_operation(
        self, classification_service: ClassificationService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_extracted_operation())

        classified = await classification_service.classify(operation)

        assert classified.candidates


class TestClassificationOutcome:
    async def test_records_the_proposal_and_advances_the_status(
        self, classification_service: ClassificationService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_extracted_operation())

        classified = await classification_service.classify(operation)

        assert classified.status is OperationStatus.CLASSIFIED
        assert classified.classification is not None
        assert len(classified.classification.tariff_code) == 8
        assert classified.error_message is None

    async def test_a_fresh_proposal_is_never_pre_confirmed(
        self, classification_service: ClassificationService, operation_repository
    ) -> None:
        """Only the review endpoint may set this flag (RF-06)."""
        operation = await operation_repository.insert(make_extracted_operation())

        classified = await classification_service.classify(operation)

        assert classified.classification is not None
        assert classified.classification.confirmed_by_user is False

    async def test_low_confidence_flags_the_operation_for_review(
        self,
        operation_repository,
        catalog_service: CatalogService,
    ) -> None:
        service = ClassificationService(
            operation_repository,
            catalog_service,
            StubTariffClassifier(confidence=0.42),
            CONFIDENCE_THRESHOLD,
        )
        operation = await operation_repository.insert(make_extracted_operation())

        classified = await service.classify(operation)

        assert classified.requires_review(CONFIDENCE_THRESHOLD)

    async def test_high_confidence_does_not_flag_for_review(
        self, classification_service: ClassificationService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_extracted_operation())

        classified = await classification_service.classify(operation)

        assert not classified.requires_review(CONFIDENCE_THRESHOLD)


class TestClassificationFailure:
    async def test_requires_an_extraction_first(
        self, classification_service: ClassificationService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(
            Operation(user_id="user-1", image_path="/uploads/photo.jpg")
        )

        with pytest.raises(InvalidStateTransitionError):
            await classification_service.classify(operation)

    async def test_rejects_reclassifying_a_finished_operation(
        self, classification_service: ClassificationService, operation_repository
    ) -> None:
        operation = make_extracted_operation()
        operation.status = OperationStatus.PEDIMENTO_GENERATED
        stored = await operation_repository.insert(operation)

        with pytest.raises(InvalidStateTransitionError):
            await classification_service.classify(stored)

    async def test_persists_a_provider_failure_before_raising(
        self, operation_repository, catalog_service: CatalogService
    ) -> None:
        service = ClassificationService(
            operation_repository,
            catalog_service,
            StubTariffClassifier(error=LlmError("Claude no respondió.")),
            CONFIDENCE_THRESHOLD,
        )
        operation = await operation_repository.insert(make_extracted_operation())

        with pytest.raises(LlmError):
            await service.classify(operation)

        stored = await operation_repository.get_by_id(str(operation.id))
        assert stored.status is OperationStatus.ERROR
        assert stored.error_message == "Claude no respondió."

    async def test_reports_when_the_catalog_has_no_candidates(
        self, classification_service: ClassificationService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(
            make_extracted_operation(
                name="zzzz", search_keywords=["zzzqx", "wwwqx"]
            )
        )

        with pytest.raises(LlmError, match="catálogo"):
            await classification_service.classify(operation)

        stored = await operation_repository.get_by_id(str(operation.id))
        assert stored.status is OperationStatus.ERROR
