"""Tests for human review and operation data capture (RF-06, RF-07, RF-08)."""

from __future__ import annotations

import pytest

from app.domain.enums import OperationStatus
from app.domain.errors import InvalidStateTransitionError, NotFoundError
from app.domain.models import (
    Importer,
    Operation,
    OperationDetails,
    Supplier,
    TariffClassification,
)
from app.services.details_service import OperationDetailsService
from app.services.review_service import ClassificationReviewService
from tests.conftest import CONFIDENCE_THRESHOLD
from tests.doubles import build_extraction

# 8518.30.01 carries a 15 % IGI in the curated catalog; 8517.13.01 is duty free.
HEADPHONES = "85183001"
SMARTPHONE = "85171301"


def make_classified_operation(
    tariff_code: str = HEADPHONES, confidence: float = 0.92
) -> Operation:
    """An operation sitting exactly where the review begins."""
    return Operation(
        user_id="user-1",
        status=OperationStatus.CLASSIFIED,
        image_path="/uploads/photo.jpg",
        extraction=build_extraction(),
        classification=TariffClassification(
            tariff_code=tariff_code,
            nico="00",
            confidence=confidence,
            rationale="Regla General 1 y Regla General 6.",
            alternatives=[],
        ),
    )


def make_details(**overrides: object) -> OperationDetails:
    defaults = {
        "invoice_value_usd": 100.0,
        "quantity": 10,
        "origin_country": "CN",
        "exchange_rate": 17.50,
        "importer": Importer(rfc="XAXX010101000", legal_name="Importadora Demo SA de CV"),
        "supplier": Supplier(name="Shenzhen Audio Co Ltd", country="CN"),
    }
    defaults.update(overrides)
    return OperationDetails(**defaults)  # type: ignore[arg-type]


class TestConfirmation:
    async def test_confirming_the_proposal_marks_it_reviewed(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_classified_operation())

        reviewed = await review_service.confirm(operation, HEADPHONES, "00")

        assert reviewed.classification is not None
        assert reviewed.classification.confirmed_by_user is True
        assert reviewed.classification.tariff_code == HEADPHONES

    async def test_confirming_a_weak_proposal_clears_the_review_flag(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        """RF-06: below the threshold, a person confirming is what unblocks."""
        operation = await operation_repository.insert(
            make_classified_operation(confidence=0.35)
        )
        assert operation.requires_review(CONFIDENCE_THRESHOLD)

        reviewed = await review_service.confirm(operation, HEADPHONES, "00")

        assert not reviewed.requires_review(CONFIDENCE_THRESHOLD)

    async def test_confirming_clears_a_previous_error(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        operation = make_classified_operation()
        operation.status = OperationStatus.ERROR
        operation.error_message = "fallo anterior"
        stored = await operation_repository.insert(operation)

        reviewed = await review_service.confirm(stored, HEADPHONES, "00")

        assert reviewed.status is OperationStatus.CLASSIFIED
        assert reviewed.error_message is None


class TestOverride:
    async def test_switching_the_code_preserves_what_the_model_proposed(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        """The demo's whole point is that the record shows who decided what."""
        operation = await operation_repository.insert(make_classified_operation())

        reviewed = await review_service.confirm(operation, SMARTPHONE, "00")

        assert reviewed.classification is not None
        assert reviewed.classification.tariff_code == SMARTPHONE
        assert reviewed.classification.original_tariff_code == HEADPHONES
        assert reviewed.classification.was_overridden

    async def test_confirming_without_changing_is_not_an_override(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_classified_operation())

        reviewed = await review_service.confirm(operation, HEADPHONES, "00")

        assert reviewed.classification is not None
        assert not reviewed.classification.was_overridden

    async def test_an_override_invalidates_a_settlement_computed_before(
        self,
        review_service: ClassificationReviewService,
        details_service: OperationDetailsService,
        operation_repository,
    ) -> None:
        """The old settlement used the old IGI rate, so it no longer applies."""
        operation = await operation_repository.insert(make_classified_operation())
        settled = await details_service.save(operation, make_details())
        assert settled.settlement is not None

        reviewed = await review_service.confirm(settled, SMARTPHONE, "00")

        assert reviewed.settlement is None

    async def test_a_second_override_keeps_the_first_original(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_classified_operation())

        once = await review_service.confirm(operation, SMARTPHONE, "00")
        twice = await review_service.confirm(once, "85182101", "00")

        assert twice.classification is not None
        assert twice.classification.original_tariff_code == HEADPHONES


class TestReviewRejections:
    async def test_rejects_a_code_outside_the_catalog(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_classified_operation())

        with pytest.raises(NotFoundError):
            await review_service.confirm(operation, "99999999", "00")

    async def test_rejects_a_nico_that_does_not_exist_for_the_code(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_classified_operation())

        with pytest.raises(NotFoundError):
            await review_service.confirm(operation, HEADPHONES, "77")

    async def test_requires_a_classification_first(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(
            Operation(user_id="user-1", image_path="/uploads/photo.jpg")
        )

        with pytest.raises(InvalidStateTransitionError):
            await review_service.confirm(operation, HEADPHONES, "00")

    async def test_rejects_editing_a_finished_operation(
        self, review_service: ClassificationReviewService, operation_repository
    ) -> None:
        operation = make_classified_operation()
        operation.status = OperationStatus.PEDIMENTO_GENERATED
        stored = await operation_repository.insert(operation)

        with pytest.raises(InvalidStateTransitionError):
            await review_service.confirm(stored, HEADPHONES, "00")


class TestDetailsAndSettlement:
    async def test_saves_the_data_and_settles_the_contributions(
        self, details_service: OperationDetailsService, operation_repository
    ) -> None:
        """100 USD at 17.50 with the 15 % IGI of heading 8518."""
        operation = await operation_repository.insert(make_classified_operation())

        settled = await details_service.save(operation, make_details())

        assert settled.operation_details is not None
        assert settled.settlement is not None
        assert settled.settlement.customs_value == 1750.00
        assert settled.settlement.igi_amount == 262.50
        assert settled.settlement.dta_amount == 14.00
        assert settled.settlement.iva_amount == 324.24
        assert settled.settlement.total == 600.74

    async def test_takes_the_igi_rate_from_the_catalog_not_the_request(
        self, details_service: OperationDetailsService, operation_repository
    ) -> None:
        """A duty-free heading must settle at zero IGI whatever the client sends."""
        operation = await operation_repository.insert(
            make_classified_operation(tariff_code=SMARTPHONE)
        )

        settled = await details_service.save(operation, make_details())

        assert settled.settlement is not None
        assert settled.settlement.igi_amount == 0.00

    async def test_resaving_recomputes_the_settlement(
        self, details_service: OperationDetailsService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_classified_operation())
        first = await details_service.save(operation, make_details())

        second = await details_service.save(first, make_details(invoice_value_usd=200.0))

        assert second.settlement is not None
        assert second.settlement.customs_value == 3500.00

    async def test_requires_a_classification_first(
        self, details_service: OperationDetailsService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(
            Operation(user_id="user-1", image_path="/uploads/photo.jpg")
        )

        with pytest.raises(InvalidStateTransitionError):
            await details_service.save(operation, make_details())

    async def test_rejects_editing_a_finished_operation(
        self, details_service: OperationDetailsService, operation_repository
    ) -> None:
        operation = make_classified_operation()
        operation.status = OperationStatus.PEDIMENTO_GENERATED
        stored = await operation_repository.insert(operation)

        with pytest.raises(InvalidStateTransitionError):
            await details_service.save(stored, make_details())
