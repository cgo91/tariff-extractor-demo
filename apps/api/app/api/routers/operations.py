"""Operation endpoints (RF-03, RF-04, RF-05, RF-10)."""

from __future__ import annotations

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import Response

from app.api.schemas.operations import (
    ClassificationUpdateRequest,
    ExtractionUpdateRequest,
    OperationDetailsRequest,
    OperationResponse,
    OperationSummaryResponse,
)
from app.core.dependencies import (
    ClassificationServiceDep,
    CurrentUserDep,
    DetailsServiceDep,
    ExtractionServiceDep,
    OperationServiceDep,
    PedimentoServiceDep,
    ReviewServiceDep,
    SettingsDep,
)
from app.domain.errors import ValidationError

router = APIRouter(prefix="/operations", tags=["operations"])

# Declared once at module level: FastAPI evaluates it at import time and
# re-evaluating it per call buys nothing.
PHOTO_UPLOAD = File(description="Fotografía del producto en JPG o PNG")


@router.post("", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def create_operation(
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    settings: SettingsDep,
    file: UploadFile = PHOTO_UPLOAD,
) -> OperationResponse:
    """Upload a product photograph and open an operation."""
    # Starlette reports the size before the body is consumed, so an oversized
    # upload is rejected without holding it all in memory.
    if file.size is not None and file.size > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes / (1024 * 1024)
        raise ValidationError(f"La imagen supera el máximo de {limit_mb:.0f} MB.")

    content = await file.read()
    operation = await operation_service.create(current_user, content, file.content_type)
    return OperationResponse.from_domain(operation, settings.confidence_threshold)


@router.get("", response_model=list[OperationSummaryResponse])
async def list_operations(
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    settings: SettingsDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[OperationSummaryResponse]:
    """List the caller's operations, newest first."""
    operations = await operation_service.list_for_user(current_user, limit)
    return [
        OperationSummaryResponse.from_domain(operation, settings.confidence_threshold)
        for operation in operations
    ]


@router.get("/{operation_id}", response_model=OperationResponse)
async def read_operation(
    operation_id: str,
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    settings: SettingsDep,
) -> OperationResponse:
    """Full detail of one operation."""
    operation = await operation_service.get_for_user(operation_id, current_user)
    return OperationResponse.from_domain(operation, settings.confidence_threshold)


@router.get("/{operation_id}/image")
async def read_operation_image(
    operation_id: str,
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
) -> Response:
    """Serve the stored photograph so the UI can show it back."""
    operation = await operation_service.get_for_user(operation_id, current_user)
    image = await operation_service.read_image(operation)
    media_type = "image/png" if operation.image_path.lower().endswith(".png") else "image/jpeg"
    return Response(content=image, media_type=media_type)


@router.post("/{operation_id}/extract", response_model=OperationResponse)
async def extract_features(
    operation_id: str,
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    extraction_service: ExtractionServiceDep,
    settings: SettingsDep,
) -> OperationResponse:
    """Run Claude vision over the photograph (RF-04)."""
    operation = await operation_service.get_for_user(operation_id, current_user)
    extracted = await extraction_service.extract(operation)
    return OperationResponse.from_domain(extracted, settings.confidence_threshold)


@router.patch("/{operation_id}/extraction", response_model=OperationResponse)
async def update_extraction(
    operation_id: str,
    payload: ExtractionUpdateRequest,
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    settings: SettingsDep,
) -> OperationResponse:
    """Apply the user's corrections to the name and function (RF-04)."""
    operation = await operation_service.get_for_user(operation_id, current_user)
    if operation.extraction is None:
        raise ValidationError("La operación todavía no tiene una extracción.")

    edited = operation.extraction.model_copy(
        update={"name": payload.name.strip(), "function": payload.function.strip()}
    )
    updated = await operation_service.update_extraction(operation, edited)
    return OperationResponse.from_domain(updated, settings.confidence_threshold)


@router.post("/{operation_id}/classify", response_model=OperationResponse)
async def classify_operation(
    operation_id: str,
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    classification_service: ClassificationServiceDep,
    settings: SettingsDep,
) -> OperationResponse:
    """Search candidates and ask Claude to choose among them (RF-05)."""
    operation = await operation_service.get_for_user(operation_id, current_user)
    classified = await classification_service.classify(operation)
    return OperationResponse.from_domain(classified, settings.confidence_threshold)


@router.patch("/{operation_id}/classification", response_model=OperationResponse)
async def confirm_classification(
    operation_id: str,
    payload: ClassificationUpdateRequest,
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    review_service: ReviewServiceDep,
    settings: SettingsDep,
) -> OperationResponse:
    """Confirm the proposal or replace it with another catalog code (RF-06)."""
    operation = await operation_service.get_for_user(operation_id, current_user)
    reviewed = await review_service.confirm(operation, payload.tariff_code, payload.nico)
    return OperationResponse.from_domain(reviewed, settings.confidence_threshold)


@router.patch("/{operation_id}/details", response_model=OperationResponse)
async def save_operation_details(
    operation_id: str,
    payload: OperationDetailsRequest,
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    details_service: DetailsServiceDep,
    settings: SettingsDep,
) -> OperationResponse:
    """Save the commercial data and settle the contributions (RF-07, RF-08)."""
    operation = await operation_service.get_for_user(operation_id, current_user)
    updated = await details_service.save(operation, payload.to_domain())
    return OperationResponse.from_domain(updated, settings.confidence_threshold)


@router.post("/{operation_id}/pedimento", response_model=OperationResponse)
async def generate_pedimento(
    operation_id: str,
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    pedimento_service: PedimentoServiceDep,
    settings: SettingsDep,
) -> OperationResponse:
    """Render the simulated pedimento PDF (RF-09)."""
    operation = await operation_service.get_for_user(operation_id, current_user)
    generated = await pedimento_service.generate(operation)
    return OperationResponse.from_domain(generated, settings.confidence_threshold)


@router.get("/{operation_id}/pedimento")
async def download_pedimento(
    operation_id: str,
    current_user: CurrentUserDep,
    operation_service: OperationServiceDep,
    pedimento_service: PedimentoServiceDep,
) -> Response:
    """Download the generated pedimento (RF-09)."""
    operation = await operation_service.get_for_user(operation_id, current_user)
    pdf = await pedimento_service.read_pdf(operation)
    filename = f"pedimento-{operation.id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        # "inline" so the browser previews it; the UI offers an explicit
        # download link alongside.
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
