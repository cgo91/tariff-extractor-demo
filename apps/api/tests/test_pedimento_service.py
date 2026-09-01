"""Tests for pedimento generation (RF-09).

The PDF engine is replaced by a renderer that captures the HTML, so these
assert on the composed document rather than on bytes nobody can read.
"""

from __future__ import annotations

import pytest

from app.domain.enums import OperationStatus
from app.domain.errors import InvalidStateTransitionError, NotFoundError
from app.domain.models import Operation
from app.services.details_service import OperationDetailsService
from app.services.pedimento_service import PedimentoService
from app.services.review_service import ClassificationReviewService
from tests.doubles import CapturingPdfRenderer, InMemoryFileStorage
from tests.test_review_and_details import (
    HEADPHONES,
    make_classified_operation,
    make_details,
)


async def make_ready_operation(
    operation_repository,
    details_service: OperationDetailsService,
    confidence: float = 0.92,
) -> Operation:
    """An operation with everything the pedimento needs."""
    operation = await operation_repository.insert(
        make_classified_operation(confidence=confidence)
    )
    return await details_service.save(operation, make_details())


class TestGeneration:
    async def test_stores_the_pdf_and_closes_the_operation(
        self,
        pedimento_service: PedimentoService,
        details_service: OperationDetailsService,
        file_storage: InMemoryFileStorage,
        operation_repository,
    ) -> None:
        ready = await make_ready_operation(operation_repository, details_service)

        generated = await pedimento_service.generate(ready)

        assert generated.status is OperationStatus.PEDIMENTO_GENERATED
        assert generated.pedimento_pdf_path is not None
        assert file_storage.exists(generated.pedimento_pdf_path)

    async def test_the_document_carries_the_settled_amounts(
        self,
        pedimento_service: PedimentoService,
        details_service: OperationDetailsService,
        pdf_renderer: CapturingPdfRenderer,
        operation_repository,
    ) -> None:
        """RF-09 acceptance: the PDF must match the persisted settlement."""
        ready = await make_ready_operation(operation_repository, details_service)

        await pedimento_service.generate(ready)

        html = pdf_renderer.rendered_html
        assert html is not None
        assert "1,750.00" in html  # valor en aduana
        assert "262.50" in html  # IGI
        assert "14.00" in html  # DTA
        assert "324.24" in html  # IVA
        assert "600.74" in html  # total

    async def test_the_document_carries_the_required_sections(
        self,
        pedimento_service: PedimentoService,
        details_service: OperationDetailsService,
        pdf_renderer: CapturingPdfRenderer,
        operation_repository,
    ) -> None:
        ready = await make_ready_operation(operation_repository, details_service)

        await pedimento_service.generate(ready)

        html = pdf_renderer.rendered_html
        assert html is not None
        for expected in (
            "8518.30.01",  # fracción, dotted
            "IMP",  # tipo de operación
            "A1",  # clave de pedimento
            "XAXX010101000",  # RFC del importador
            "Importadora Demo SA de CV",
            "Shenzhen Audio Co Ltd",  # proveedor
            "Pza",  # UMT
            "CN",  # país de origen
            "Documento simulado con fines de demostración",
        ):
            assert expected in html, expected

    async def test_records_a_manual_override_on_the_document(
        self,
        pedimento_service: PedimentoService,
        review_service: ClassificationReviewService,
        details_service: OperationDetailsService,
        pdf_renderer: CapturingPdfRenderer,
        operation_repository,
    ) -> None:
        operation = await operation_repository.insert(make_classified_operation())
        overridden = await review_service.confirm(operation, "85171301", "00")
        ready = await details_service.save(overridden, make_details())

        await pedimento_service.generate(ready)

        html = pdf_renderer.rendered_html
        assert html is not None
        assert "8517.13.01" in html  # the code the reviewer chose
        assert "8518.30.01" in html  # the code the model had proposed
        assert "sustituida por el usuario" in html


class TestPedimentoNumber:
    async def test_is_stable_across_regenerations(
        self,
        pedimento_service: PedimentoService,
        details_service: OperationDetailsService,
        operation_repository,
    ) -> None:
        """The number printed on a document must not change under it."""
        ready = await make_ready_operation(operation_repository, details_service)

        first = pedimento_service.build_number(ready)
        second = pedimento_service.build_number(ready)

        assert first == second

    async def test_has_the_expected_shape(
        self,
        pedimento_service: PedimentoService,
        details_service: OperationDetailsService,
        operation_repository,
    ) -> None:
        ready = await make_ready_operation(operation_repository, details_service)

        number = pedimento_service.build_number(ready)

        year, section, licence, sequence = number.split(" ")
        assert len(year) == 2 and year.isdigit()
        assert len(section) == 2
        assert len(licence) == 4
        assert len(sequence) == 7 and sequence.isdigit()


class TestPreconditions:
    async def test_blocks_a_proposal_that_still_requires_review(
        self,
        pedimento_service: PedimentoService,
        details_service: OperationDetailsService,
        operation_repository,
    ) -> None:
        """RF-06: below the threshold there is no pedimento without a human."""
        ready = await make_ready_operation(
            operation_repository, details_service, confidence=0.31
        )

        with pytest.raises(InvalidStateTransitionError, match="revisión manual"):
            await pedimento_service.generate(ready)

    async def test_allows_it_once_a_person_confirms(
        self,
        pedimento_service: PedimentoService,
        review_service: ClassificationReviewService,
        details_service: OperationDetailsService,
        operation_repository,
    ) -> None:
        operation = await operation_repository.insert(
            make_classified_operation(confidence=0.31)
        )
        confirmed = await review_service.confirm(operation, HEADPHONES, "00")
        ready = await details_service.save(confirmed, make_details())

        generated = await pedimento_service.generate(ready)

        assert generated.status is OperationStatus.PEDIMENTO_GENERATED

    async def test_requires_the_operation_data(
        self, pedimento_service: PedimentoService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_classified_operation())

        with pytest.raises(InvalidStateTransitionError, match="datos de la operación"):
            await pedimento_service.generate(operation)

    async def test_requires_a_classification(
        self, pedimento_service: PedimentoService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(
            Operation(user_id="user-1", image_path="/uploads/photo.jpg")
        )

        with pytest.raises(InvalidStateTransitionError, match="clasificar"):
            await pedimento_service.generate(operation)


class TestDownload:
    async def test_returns_the_stored_bytes(
        self,
        pedimento_service: PedimentoService,
        details_service: OperationDetailsService,
        operation_repository,
    ) -> None:
        ready = await make_ready_operation(operation_repository, details_service)
        generated = await pedimento_service.generate(ready)

        pdf = await pedimento_service.read_pdf(generated)

        assert pdf.startswith(b"%PDF")

    async def test_reports_a_pedimento_that_was_never_generated(
        self, pedimento_service: PedimentoService, operation_repository
    ) -> None:
        operation = await operation_repository.insert(make_classified_operation())

        with pytest.raises(NotFoundError):
            await pedimento_service.read_pdf(operation)

    async def test_reports_a_file_missing_from_storage(
        self,
        pedimento_service: PedimentoService,
        details_service: OperationDetailsService,
        file_storage: InMemoryFileStorage,
        operation_repository,
    ) -> None:
        ready = await make_ready_operation(operation_repository, details_service)
        generated = await pedimento_service.generate(ready)
        file_storage.files.clear()

        with pytest.raises(NotFoundError):
            await pedimento_service.read_pdf(generated)
