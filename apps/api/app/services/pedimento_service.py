"""Pedimento generation (RF-09).

Composes the document context, renders the Jinja2 template, and hands the HTML
to a :class:`PdfRenderer`. The service knows nothing about WeasyPrint.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.domain.enums import OperationStatus
from app.domain.errors import InvalidStateTransitionError, NotFoundError
from app.domain.models import Operation
from app.repositories.base import OperationRepository
from app.services.catalog_service import CatalogService
from app.services.pdf.base import PdfRenderer
from app.services.storage.base import FileStorage
from app.services.storage.local_storage import PEDIMENTOS

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "pedimento.html"

# Mock header values. A real pedimento draws these from the customs broker's
# credentials and the entry point; the demo has neither.
CUSTOMS_OFFICE = "470 · AICM, Ciudad de México"
OPERATION_TYPE = "IMP"
PEDIMENTO_KEY = "A1"
REGIME = "IMD · Definitivo de importación"
CUSTOMS_SECTION = "47"
BROKER_LICENCE = "3512"


class PedimentoService:
    """Generates and retrieves the simulated pedimento PDF."""

    def __init__(
        self,
        operation_repository: OperationRepository,
        catalog_service: CatalogService,
        file_storage: FileStorage,
        pdf_renderer: PdfRenderer,
        confidence_threshold: float,
    ) -> None:
        self._operations = operation_repository
        self._catalog = catalog_service
        self._storage = file_storage
        self._renderer = pdf_renderer
        self._confidence_threshold = confidence_threshold
        self._templates = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(["html"]),
            # A missing context key must fail loudly rather than print an empty
            # box on a document that looks official.
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def generate(self, operation: Operation) -> Operation:
        """Render the pedimento and store it.

        Raises:
            InvalidStateTransitionError: when the operation is not ready, or
                when the classification still requires manual review (RF-06).
            PdfGenerationError: when the renderer fails.
        """
        self._assert_ready(operation)

        tariff_item = await self._catalog.get_item(
            operation.classification.tariff_code,  # type: ignore[union-attr]
            operation.classification.nico,  # type: ignore[union-attr]
        )
        context = self._build_context(operation, tariff_item)
        html = self._templates.get_template(TEMPLATE_NAME).render(**context)
        pdf = self._renderer.render(html)

        path = self._storage.save(PEDIMENTOS, f"{operation.id}.pdf", pdf)
        operation.pedimento_pdf_path = path
        operation.status = OperationStatus.PEDIMENTO_GENERATED
        operation.error_message = None

        logger.info(
            "Pedimento %s generado para la operación %s (%d bytes)",
            context["header"]["number"],
            operation.id,
            len(pdf),
        )
        return await self._operations.update(operation)

    async def read_pdf(self, operation: Operation) -> bytes:
        """Return the stored PDF.

        Raises:
            NotFoundError: when it has not been generated, or the file is gone.
        """
        if operation.pedimento_pdf_path is None:
            raise NotFoundError("La operación todavía no tiene un pedimento generado.")
        try:
            return self._storage.load(operation.pedimento_pdf_path)
        except FileNotFoundError as exc:
            raise NotFoundError(
                "El archivo del pedimento ya no está disponible en el servidor."
            ) from exc

    def build_number(self, operation: Operation) -> str:
        """Derive a stable 15-digit pedimento number for the operation.

        Real numbers are assigned by the broker's sequence; this one is derived
        from the operation id so that regenerating the document does not change
        the number printed on it.
        """
        year = operation.created_at.astimezone(UTC).strftime("%y")
        digits = "".join(character for character in str(operation.id) if character.isdigit())
        sequence = (digits or "0").rjust(7, "0")[-7:]
        return f"{year} {CUSTOMS_SECTION} {BROKER_LICENCE} {sequence}"

    # --- internals ---------------------------------------------------------

    def _assert_ready(self, operation: Operation) -> None:
        """Check every precondition, naming the missing step."""
        if operation.classification is None:
            raise InvalidStateTransitionError("Primero hay que clasificar la mercancía.")
        if operation.operation_details is None or operation.settlement is None:
            raise InvalidStateTransitionError(
                "Faltan los datos de la operación para poder liquidarla."
            )
        # RF-06: a weak proposal cannot reach a document until a person owns it.
        if operation.requires_review(self._confidence_threshold):
            raise InvalidStateTransitionError(
                "La clasificación requiere revisión manual. Confirma una fracción "
                "antes de generar el pedimento."
            )

    def _build_context(self, operation: Operation, tariff_item) -> dict:
        """Assemble the template context, formatting every value for print."""
        classification = operation.classification
        details = operation.operation_details
        settlement = operation.settlement
        extraction = operation.extraction
        assert classification and details and settlement  # guaranteed by _assert_ready

        return {
            "header": {
                "number": self.build_number(operation),
                "operation_type": OPERATION_TYPE,
                "pedimento_key": PEDIMENTO_KEY,
                "customs_office": CUSTOMS_OFFICE,
                "regime": REGIME,
                "issued_at": datetime.now(UTC).strftime("%d/%m/%Y"),
            },
            "importer": {
                "rfc": details.importer.rfc,
                "legal_name": details.importer.legal_name,
            },
            "supplier": {
                "name": details.supplier.name,
                "country": details.supplier.country,
            },
            "item": {
                "formatted_code": tariff_item.formatted_code,
                "nico": classification.nico,
                "description": tariff_item.description,
                "unit_of_measure": tariff_item.unit_of_measure,
                "igi_percentage": f"{tariff_item.igi_rate * 100:.0f} %",
            },
            "details": {
                "invoice_value_usd": _money(details.invoice_value_usd),
                "quantity": f"{details.quantity:,}".replace(",", " "),
                "origin_country": details.origin_country,
                "exchange_rate": f"{details.exchange_rate:.4f}",
            },
            "settlement": {
                "customs_value": _money(settlement.customs_value),
                "igi_amount": _money(settlement.igi_amount),
                "dta_amount": _money(settlement.dta_amount),
                "iva_amount": _money(settlement.iva_amount),
                "total": _money(settlement.total),
            },
            "classification": {
                "rationale": classification.rationale,
                "confidence": f"{classification.confidence * 100:.0f} %",
                "confirmed_by_user": classification.confirmed_by_user,
                "original_code": (
                    _format_code(classification.original_tariff_code)
                    if classification.was_overridden
                    else None
                ),
                "was_overridden": classification.was_overridden,
            },
            "product": {
                "name": extraction.name if extraction else None,
                "brand": extraction.brand if extraction else None,
                "model": extraction.model if extraction else None,
            },
        }


def _money(amount: float) -> str:
    """Format an amount with thousands separators and two decimals."""
    return f"{amount:,.2f}"


def _format_code(tariff_code: str | None) -> str | None:
    """Render an 8 digit code in the dotted form used on printed documents."""
    if tariff_code is None:
        return None
    return f"{tariff_code[:4]}.{tariff_code[4:6]}.{tariff_code[6:8]}"
