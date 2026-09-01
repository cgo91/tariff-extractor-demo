"""Domain level exception hierarchy.

Services raise these instead of ``HTTPException`` so that the domain layer stays
free of HTTP concerns. ``app.main`` registers a single handler that maps every
subclass to its ``status_code``.
"""


class DomainError(Exception):
    """Base class for every expected, business-level failure."""

    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """A requested aggregate does not exist."""

    status_code = 404
    code = "not_found"


class AuthenticationError(DomainError):
    """Credentials are missing or invalid."""

    status_code = 401
    code = "authentication_error"


class ValidationError(DomainError):
    """The request is syntactically valid but violates a business rule."""

    status_code = 422
    code = "validation_error"


class InvalidStateTransitionError(DomainError):
    """The operation is not in a status that allows the requested action."""

    status_code = 409
    code = "invalid_state_transition"


class LlmError(DomainError):
    """The Claude API call failed or returned an unusable result."""

    status_code = 502
    code = "llm_error"


class ClassificationOutOfCandidatesError(LlmError):
    """The model insisted on a tariff code outside the candidate list."""

    code = "classification_out_of_candidates"


class PdfGenerationError(DomainError):
    """The pedimento PDF could not be rendered."""

    status_code = 500
    code = "pdf_generation_error"
