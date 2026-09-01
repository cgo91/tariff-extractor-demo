"""WeasyPrint implementation of :class:`PdfRenderer`."""

from __future__ import annotations

import logging

from app.domain.errors import PdfGenerationError
from app.services.pdf.base import PdfRenderer

logger = logging.getLogger(__name__)


class WeasyPrintRenderer(PdfRenderer):
    """Renders HTML with WeasyPrint's Pango/Cairo backend.

    The import is deferred to the first render because WeasyPrint loads its
    system libraries at import time: a machine without them can still start the
    API and use every endpoint that does not produce a PDF.
    """

    def render(self, html: str, base_url: str | None = None) -> bytes:
        try:
            from weasyprint import HTML
        except (ImportError, OSError) as exc:
            logger.exception("WeasyPrint no está disponible")
            raise PdfGenerationError(
                "El servidor no tiene disponibles las librerías de WeasyPrint. "
                "Genera el pedimento desde el contenedor Docker."
            ) from exc

        try:
            return HTML(string=html, base_url=base_url).write_pdf()
        except Exception as exc:  # noqa: BLE001 - engine failures are opaque
            logger.exception("Fallo al renderizar el pedimento")
            raise PdfGenerationError(f"No se pudo generar el PDF: {exc}") from exc
