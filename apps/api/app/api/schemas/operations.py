"""Request and response DTOs for the operation endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas.catalog import TariffItemResponse
from app.domain.enums import OperationStatus
from app.domain.models import (
    ClassificationAlternative,
    Importer,
    Operation,
    OperationDetails,
    ProductExtraction,
    Settlement,
    Supplier,
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
    original_tariff_code: str | None
    was_overridden: bool
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
            original_tariff_code=classification.original_tariff_code,
            was_overridden=classification.was_overridden,
            requires_review=(
                not classification.confirmed_by_user and classification.confidence < threshold
            ),
            confidence_threshold=threshold,
        )


class ClassificationUpdateRequest(BaseModel):
    """The reviewer's decision (RF-06).

    ``confirmed_by_user`` is accepted for symmetry with the PRD payload but is
    not read: reaching this endpoint *is* the confirmation, and a client that
    sent ``false`` would be asking to record a review that did not happen.
    """

    tariff_code: str = Field(pattern=r"^\d{8}$")
    nico: str = Field(pattern=r"^\d{2}$")
    confirmed_by_user: bool = True


class ImporterPayload(BaseModel):
    """Importing party."""

    rfc: str = Field(min_length=12, max_length=13)
    legal_name: str = Field(min_length=2, max_length=200)


class SupplierPayload(BaseModel):
    """Foreign shipping party."""

    name: str = Field(min_length=2, max_length=200)
    country: str = Field(pattern=r"^[A-Za-z]{2}$")


class OperationDetailsRequest(BaseModel):
    """Commercial data captured before generating the pedimento (RF-07)."""

    invoice_value_usd: float = Field(gt=0, le=100_000_000)
    quantity: int = Field(gt=0, le=1_000_000)
    origin_country: str = Field(pattern=r"^[A-Za-z]{2}$")
    exchange_rate: float = Field(gt=0, le=1000)
    importer: ImporterPayload
    supplier: SupplierPayload

    def to_domain(self) -> OperationDetails:
        """Build the domain model, normalising the country codes to uppercase."""
        return OperationDetails(
            invoice_value_usd=self.invoice_value_usd,
            quantity=self.quantity,
            origin_country=self.origin_country.upper(),
            exchange_rate=self.exchange_rate,
            importer=Importer(
                rfc=self.importer.rfc.upper(), legal_name=self.importer.legal_name
            ),
            supplier=Supplier(
                name=self.supplier.name, country=self.supplier.country.upper()
            ),
        )


class OperationDetailsResponse(BaseModel):
    """Commercial data as exposed by the API."""

    invoice_value_usd: float
    quantity: int
    origin_country: str
    exchange_rate: float
    importer: ImporterPayload
    supplier: SupplierPayload

    @classmethod
    def from_domain(cls, details: OperationDetails) -> OperationDetailsResponse:
        return cls(
            invoice_value_usd=details.invoice_value_usd,
            quantity=details.quantity,
            origin_country=details.origin_country,
            exchange_rate=details.exchange_rate,
            importer=ImporterPayload(**details.importer.model_dump()),
            supplier=SupplierPayload(**details.supplier.model_dump()),
        )


class SettlementResponse(BaseModel):
    """Computed contributions in MXN (RF-08)."""

    customs_value: float
    igi_amount: float
    dta_amount: float
    iva_amount: float
    total: float

    @classmethod
    def from_domain(cls, settlement: Settlement) -> SettlementResponse:
        return cls(**settlement.model_dump())


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
    operation_details: OperationDetailsResponse | None
    settlement: SettlementResponse | None
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
            operation_details=(
                OperationDetailsResponse.from_domain(operation.operation_details)
                if operation.operation_details
                else None
            ),
            settlement=(
                SettlementResponse.from_domain(operation.settlement)
                if operation.settlement
                else None
            ),
            error_message=operation.error_message,
            has_pedimento=operation.pedimento_pdf_path is not None,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
        )
