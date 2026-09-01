"""Request and response DTOs for the operation endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas.catalog import TariffItemResponse
from app.domain.enums import OperationStatus
from app.domain.models import (
    ClassificationAlternative,
    Operation,
    ProductExtraction,
    TariffClassification,
)


class ExtractionResponse(BaseModel):
    """Product features as exposed by the API."""

    name: str
    brand: str | None
    model: str | None
    material: str | None
    function: str
    technical_specs: list[str]
    visible_text: str | None
    search_keywords: list[str]

    @classmethod
    def from_domain(cls, extraction: ProductExtraction) -> ExtractionResponse:
        return cls(**extraction.model_dump())


class ExtractionUpdateRequest(BaseModel):
    """User corrections to the extraction before classifying (RF-04).

    Only the two fields the review card exposes are editable; everything else
    stays as Claude reported it.
    """

    name: str = Field(min_length=2, max_length=200)
    function: str = Field(min_length=2, max_length=500)


class ClassificationAlternativeResponse(BaseModel):
    """A discarded tariff code and the reason it was discarded."""

    tariff_code: str
    formatted_code: str
    nico: str
    reason: str

    @classmethod
    def from_domain(
        cls, alternative: ClassificationAlternative
    ) -> ClassificationAlternativeResponse:
        code = alternative.tariff_code
        return cls(
            tariff_code=code,
            formatted_code=f"{code[:4]}.{code[4:6]}.{code[6:8]}",
            nico=alternative.nico,
            reason=alternative.reason,
        )


class ClassificationResponse(BaseModel):
    """The proposal, its confidence and the review flag."""

    tariff_code: str
    formatted_code: str
    nico: str
    confidence: float
    rationale: str
    alternatives: list[ClassificationAlternativeResponse]
    confirmed_by_user: bool
    requires_review: bool = Field(
        description="True while confidence is below the threshold and nobody has confirmed"
    )
    confidence_threshold: float = Field(
        description="Threshold that produced requires_review; the UI draws it on the meter"
    )

    @classmethod
    def from_domain(
        cls, classification: TariffClassification, threshold: float
    ) -> ClassificationResponse:
        code = classification.tariff_code
        return cls(
            tariff_code=code,
            formatted_code=f"{code[:4]}.{code[4:6]}.{code[6:8]}",
            nico=classification.nico,
            confidence=classification.confidence,
            rationale=classification.rationale,
            alternatives=[
                ClassificationAlternativeResponse.from_domain(alternative)
                for alternative in classification.alternatives
            ],
            confirmed_by_user=classification.confirmed_by_user,
            requires_review=(
                not classification.confirmed_by_user and classification.confidence < threshold
            ),
            confidence_threshold=threshold,
        )


class OperationSummaryResponse(BaseModel):
    """Row of the history table (RF-10)."""

    id: str
    status: OperationStatus
    product_name: str | None
    tariff_code: str | None
    formatted_code: str | None
    confidence: float | None
    has_pedimento: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, operation: Operation) -> OperationSummaryResponse:
        classification = operation.classification
        code = classification.tariff_code if classification else None
        return cls(
            id=str(operation.id),
            status=operation.status,
            product_name=operation.extraction.name if operation.extraction else None,
            tariff_code=code,
            formatted_code=f"{code[:4]}.{code[4:6]}.{code[6:8]}" if code else None,
            confidence=classification.confidence if classification else None,
            has_pedimento=operation.pedimento_pdf_path is not None,
            created_at=operation.created_at,
        )


class OperationResponse(BaseModel):
    """Full detail of an operation."""

    id: str
    status: OperationStatus
    image_url: str
    extraction: ExtractionResponse | None
    candidates: list[TariffItemResponse]
    classification: ClassificationResponse | None
    error_message: str | None
    has_pedimento: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, operation: Operation, threshold: float) -> OperationResponse:
        return cls(
            id=str(operation.id),
            status=operation.status,
            image_url=f"/operations/{operation.id}/image",
            extraction=(
                ExtractionResponse.from_domain(operation.extraction)
                if operation.extraction
                else None
            ),
            candidates=[
                TariffItemResponse.from_domain(candidate) for candidate in operation.candidates
            ],
            classification=(
                ClassificationResponse.from_domain(operation.classification, threshold)
                if operation.classification
                else None
            ),
            error_message=operation.error_message,
            has_pedimento=operation.pedimento_pdf_path is not None,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
        )
