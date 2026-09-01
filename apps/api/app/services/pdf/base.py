"""PDF rendering abstraction.

``PedimentoService`` composes the document as HTML and hands it here. Keeping
the engine behind an interface is what makes the WeasyPrint system dependency a
deployment detail rather than a design decision: a ReportLab implementation
would slot in without the service noticing.
"""

from abc import ABC, abstractmethod


class PdfRenderer(ABC):
    """Turns an HTML document into PDF bytes."""

    @abstractmethod
    def render(self, html: str, base_url: str | None = None) -> bytes:
        """Render the document.

        Args:
            html: A complete HTML document, styles included.
            base_url: Root for resolving relative asset references, if any.

        Raises:
            PdfGenerationError: when the engine cannot produce a document.
        """
