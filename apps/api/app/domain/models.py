"""Domain models.

These are plain Pydantic models: they know nothing about HTTP, MongoDB or the
Anthropic SDK. Repositories map them to and from documents, routers map them to
and from API DTOs, and the Claude integration reuses ``ProductExtraction`` and
``TariffClassification`` as structured-output schemas so that a single
definition governs validation everywhere.

Monetary amounts are stored as ``float`` already rounded to two decimals.
``DutyCalculator`` performs the arithmetic with ``Decimal`` and only converts on
the way out, which keeps the maths exact while staying JSON and BSON friendly.
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import OperationStatus

# A Mexican tariff code is exactly 8 digits; the NICO discriminator is 2 digits.
TariffCode = Annotated[str, Field(pattern=r"^\d{8}$")]
NicoCode = Annotated[str, Field(pattern=r"^\d{2}$")]
CountryCode = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]


def utc_now() -> datetime:
    """Return the current UTC timestamp (used as a default factory)."""
    return datetime.now(UTC)


class User(BaseModel):
    """An authenticated operator. The MVP seeds exactly one."""

    id: str | None = None
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)


class TariffItem(BaseModel):
    """A single entry of the TIGIE catalog (collection ``tariff_items``)."""

    tariff_code: TariffCode
    nico: NicoCode = "00"
    description: str
    heading_description: str = ""
    chapter: str
    unit_of_measure: str = "Pza"
    igi_rate: float = 0.0
    iva_rate: float = 0.16
    is_active: bool = True

    @property
    def formatted_code(self) -> str:
        """Return the code in the dotted form used on printed documents."""
        code = self.tariff_code
        return f"{code[:4]}.{code[4:6]}.{code[6:8]}"


class ProductExtraction(BaseModel):
    """Product features extracted from the photograph by Claude vision.

    Also used as the structured-output schema of the extraction call, so the
    model literally cannot return a differently shaped payload. No field
    carries a default: every one is required, and the ones that may be unknown
    are nullable instead. That forces the model to state "not visible" rather
    than silently omitting a key.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Nombre comercial del producto, en español")
    brand: str | None = Field(description="Marca, si es legible; null si no se distingue")
    model: str | None = Field(description="Modelo o número de parte; null si no se distingue")
    material: str | None = Field(description="Material predominante; null si no se puede saber")
    function: str = Field(description="Para qué sirve el producto, en una frase")
    technical_specs: list[str] = Field(
        description="Características técnicas observables (conectores, potencia, conectividad)"
    )
    visible_text: str | None = Field(
        description="Texto legible sobre el producto, su etiqueta o su caja; null si no hay"
    )
    search_keywords: list[str] = Field(
        description="Entre 4 y 8 palabras clave en español para buscar en el catálogo TIGIE"
    )


class ClassificationAlternative(BaseModel):
    """A runner-up tariff code the user may switch to."""

    model_config = ConfigDict(extra="forbid")

    tariff_code: TariffCode
    nico: NicoCode
    reason: str = Field(description="Por qué esta fracción es plausible pero no la elegida")


class TariffClassificationProposal(BaseModel):
    """What Claude returns from the classification call.

    Deliberately excludes ``confirmed_by_user``: that flag belongs to the human
    review step and the model must have no way to set it.
    """

    model_config = ConfigDict(extra="forbid")

    tariff_code: TariffCode = Field(description="Fracción de 8 dígitos, sin puntos")
    nico: NicoCode = Field(description="NICO de 2 dígitos")
    confidence: float = Field(ge=0.0, le=1.0, description="Confianza entre 0 y 1")
    rationale: str = Field(
        description="Justificación citando las Reglas Generales 1 y 6 de la LIGIE"
    )
    alternatives: list[ClassificationAlternative] = Field(
        description="Hasta 3 fracciones alternas consideradas y descartadas"
    )


class TariffClassification(TariffClassificationProposal):
    """The proposal plus the outcome of the human review (RF-06)."""

    confirmed_by_user: bool = False


class Importer(BaseModel):
    """Party importing the goods (mock data in the demo)."""

    rfc: str
    legal_name: str


class Supplier(BaseModel):
    """Foreign party shipping the goods (mock data in the demo)."""

    name: str
    country: CountryCode


class OperationDetails(BaseModel):
    """Commercial data captured by the user before generating the pedimento."""

    invoice_value_usd: float = Field(gt=0)
    quantity: int = Field(gt=0)
    origin_country: CountryCode
    exchange_rate: float = Field(gt=0)
    importer: Importer
    supplier: Supplier


class Settlement(BaseModel):
    """Computed contributions, rounded to two decimals (MXN)."""

    customs_value: float
    igi_amount: float
    dta_amount: float
    iva_amount: float
    total: float


class Operation(BaseModel):
    """The aggregate root: one photo, one classification, one pedimento."""

    id: str | None = None
    user_id: str
    status: OperationStatus = OperationStatus.CREATED
    image_path: str
    extraction: ProductExtraction | None = None
    candidates: list[TariffItem] = Field(default_factory=list)
    classification: TariffClassification | None = None
    operation_details: OperationDetails | None = None
    settlement: Settlement | None = None
    pedimento_pdf_path: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def requires_review(self, threshold: float) -> bool:
        """Return True when the proposal is too weak to proceed unconfirmed."""
        if self.classification is None:
            return True
        if self.classification.confirmed_by_user:
            return False
        return self.classification.confidence < threshold
