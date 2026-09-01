"""Anthropic Claude implementations of the LLM contracts (RF-04, RF-05).

Both calls use the SDK's structured-output helper (``messages.parse`` with an
``output_format`` model), so a malformed JSON payload is not a failure mode we
have to handle: the response is either a validated Pydantic instance or an
error.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.domain.errors import ClassificationOutOfCandidatesError, LlmError
from app.domain.models import (
    ProductExtraction,
    TariffClassificationProposal,
    TariffItem,
)
from app.integrations.llm.base import TariffClassifier, VisionExtractor
from app.integrations.llm.prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
    build_classification_prompt,
    build_retry_prompt,
)

logger = logging.getLogger(__name__)

TResult = TypeVar("TResult", bound=BaseModel)

# Generous enough for a justification paragraph plus alternatives, small enough
# that a runaway response cannot stall the request past the 20 s budget.
MAX_TOKENS = 4096


class ClaudeCaller:
    """Shared plumbing for the Claude-backed integrations.

    Owns two responsibilities the concrete classes should not repeat: issuing a
    structured-output request, and translating SDK exceptions into
    :class:`LlmError` so the services never import ``anthropic``.
    """

    # Reasoning effort is a fairly new request field. If the installed SDK or
    # the account's model does not accept it, the first call downgrades once
    # and every later call skips it, rather than failing the demo outright.
    _effort_supported = True

    def __init__(self, client: anthropic.AsyncAnthropic, model: str, effort: str) -> None:
        self._client = client
        self._model = model
        self._effort = effort

    async def parse(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        output_format: type[TResult],
    ) -> TResult:
        """Send a request whose response is validated against ``output_format``."""
        request: dict[str, Any] = {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": messages,
            "output_format": output_format,
        }

        try:
            if type(self)._effort_supported:
                try:
                    response = await self._client.messages.parse(
                        **request, output_config={"effort": self._effort}
                    )
                except TypeError:
                    ClaudeCaller._effort_supported = False
                    logger.warning(
                        "El SDK instalado no acepta output_config junto con "
                        "output_format; se continuará con el esfuerzo por defecto."
                    )
                    response = await self._client.messages.parse(**request)
            else:
                response = await self._client.messages.parse(**request)
        except anthropic.APIError as exc:
            raise self._to_domain_error(exc) from exc

        return self._read_parsed(response, output_format)

    # --- internals ---------------------------------------------------------

    def _read_parsed(self, response: Any, output_format: type[TResult]) -> TResult:
        """Extract the validated payload, or explain why there is none."""
        if getattr(response, "stop_reason", None) == "refusal":
            raise LlmError(
                "Claude declinó procesar la imagen. Prueba con otra fotografía "
                "del producto."
            )

        parsed = getattr(response, "parsed_output", None)
        if isinstance(parsed, output_format):
            return parsed

        # Defensive: a response that hit the token ceiling arrives unparsed.
        if getattr(response, "stop_reason", None) == "max_tokens":
            raise LlmError(
                "La respuesta de Claude se truncó antes de completarse. Vuelve a intentarlo."
            )

        raise LlmError("Claude no devolvió una respuesta con el formato esperado.")

    @staticmethod
    def _to_domain_error(exc: anthropic.APIError) -> LlmError:
        """Map SDK exceptions to a message the operator can act on."""
        if isinstance(exc, anthropic.AuthenticationError):
            return LlmError("La API key de Anthropic es inválida o no está configurada.")
        if isinstance(exc, anthropic.PermissionDeniedError):
            return LlmError("La API key no tiene permiso para usar este modelo.")
        if isinstance(exc, anthropic.NotFoundError):
            return LlmError("El modelo configurado en CLAUDE_MODEL no existe.")
        if isinstance(exc, anthropic.RateLimitError):
            return LlmError("Se alcanzó el límite de peticiones a Claude. Reintenta en un momento.")
        if isinstance(exc, anthropic.APIConnectionError):
            return LlmError("No se pudo contactar a la API de Anthropic. Revisa la conexión.")
        if isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500:
            return LlmError("La API de Anthropic devolvió un error temporal. Reintenta.")

        logger.exception("Llamada a Claude fallida")
        return LlmError(f"La llamada a Claude falló: {exc}")


class ClaudeVisionExtractor(ClaudeCaller, VisionExtractor):
    """Extracts product features from a photograph (RF-04)."""

    async def extract(self, image: bytes, media_type: str) -> ProductExtraction:
        encoded = base64.standard_b64encode(image).decode("utf-8")
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": encoded,
                        },
                    },
                    {"type": "text", "text": EXTRACTION_USER_PROMPT},
                ],
            }
        ]

        return await self.parse(
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=messages,
            output_format=ProductExtraction,
        )


class ClaudeTariffClassifier(ClaudeCaller, TariffClassifier):
    """Picks a tariff code from a closed candidate list (RF-05).

    The model is told to choose from the list, but being told is not a
    guarantee. The choice is verified against the list, and a single corrective
    turn is allowed before the operation is marked as failed.
    """

    async def classify(
        self,
        extraction: ProductExtraction,
        candidates: list[TariffItem],
    ) -> TariffClassificationProposal:
        if not candidates:
            raise LlmError(
                "No se encontraron fracciones candidatas en el catálogo para esta mercancía."
            )

        valid_codes = {item.tariff_code for item in candidates}
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": build_classification_prompt(extraction, candidates)}
        ]

        proposal = await self._propose(messages)
        if proposal.tariff_code in valid_codes:
            return self._align_nico(proposal, candidates)

        logger.warning(
            "Claude propuso %s fuera de los candidatos; reintentando una vez",
            proposal.tariff_code,
        )
        messages.append({"role": "assistant", "content": proposal.model_dump_json()})
        messages.append(
            {"role": "user", "content": build_retry_prompt(candidates, proposal.tariff_code)}
        )

        retried = await self._propose(messages)
        if retried.tariff_code not in valid_codes:
            raise ClassificationOutOfCandidatesError(
                f"Claude insistió en la fracción {retried.tariff_code}, que no está "
                "entre los candidatos del catálogo."
            )

        return self._align_nico(retried, candidates)

    async def _propose(self, messages: list[dict[str, Any]]) -> TariffClassificationProposal:
        return await self.parse(
            system=CLASSIFICATION_SYSTEM_PROMPT,
            messages=messages,
            output_format=TariffClassificationProposal,
        )

    @staticmethod
    def _align_nico(
        proposal: TariffClassificationProposal, candidates: list[TariffItem]
    ) -> TariffClassificationProposal:
        """Snap the NICO to one that actually exists for the chosen code.

        The tariff code is validated against the candidate list, but the NICO is
        a second field the model can get wrong on its own. Correcting it here
        keeps the downstream catalog lookup from failing on an otherwise good
        classification.
        """
        available = [item for item in candidates if item.tariff_code == proposal.tariff_code]
        if any(item.nico == proposal.nico for item in available):
            return proposal

        corrected = available[0].nico
        logger.info(
            "NICO %s no existe para %s; se ajusta a %s",
            proposal.nico,
            proposal.tariff_code,
            corrected,
        )
        try:
            return proposal.model_copy(update={"nico": corrected})
        except PydanticValidationError as exc:  # pragma: no cover - catalog invariant
            raise LlmError("El catálogo tiene un NICO con formato inválido.") from exc
