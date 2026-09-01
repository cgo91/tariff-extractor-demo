"""Tests for the candidate guardrail in the Claude classifier (RF-05).

The Anthropic client is replaced by a fake whose ``messages.parse`` returns
canned proposals. That exercises the retry logic — the part that actually
protects the demo — without a network call or an API key.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.domain.errors import ClassificationOutOfCandidatesError, LlmError
from app.domain.models import TariffClassificationProposal, TariffItem
from app.integrations.llm.claude_client import ClaudeTariffClassifier
from tests.doubles import build_extraction


def make_proposal(tariff_code: str, nico: str = "00") -> TariffClassificationProposal:
    return TariffClassificationProposal(
        tariff_code=tariff_code,
        nico=nico,
        confidence=0.9,
        rationale="Regla General 1 y Regla General 6.",
        alternatives=[],
    )


class FakeResponse:
    """Mimics the shape the SDK returns from ``messages.parse``."""

    def __init__(self, parsed_output: Any, stop_reason: str = "end_turn") -> None:
        self.parsed_output = parsed_output
        self.stop_reason = stop_reason


class FakeMessages:
    """Serves a scripted sequence of responses and records the requests."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    async def parse(self, **kwargs: Any) -> FakeResponse:
        self.requests.append(kwargs)
        if not self._responses:
            raise AssertionError("El clasificador pidió más respuestas de las previstas")
        return self._responses.pop(0)


class FakeAnthropicClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.messages = FakeMessages(responses)


@pytest.fixture
def candidates(catalog_items: list[TariffItem]) -> list[TariffItem]:
    """Three real headphone-adjacent tariff items to choose among."""
    wanted = {"85183001", "85183099", "85182101"}
    return [item for item in catalog_items if item.tariff_code in wanted]


def build_classifier(responses: list[FakeResponse]) -> tuple[ClaudeTariffClassifier, FakeMessages]:
    client = FakeAnthropicClient(responses)
    classifier = ClaudeTariffClassifier(client, "claude-opus-5", "high")  # type: ignore[arg-type]
    return classifier, client.messages


class TestHappyPath:
    async def test_accepts_a_code_inside_the_candidate_list(
        self, candidates: list[TariffItem]
    ) -> None:
        classifier, messages = build_classifier([FakeResponse(make_proposal("85183001"))])

        result = await classifier.classify(build_extraction(), candidates)

        assert result.tariff_code == "85183001"
        assert len(messages.requests) == 1, "no debe reintentar cuando la fracción es válida"

    async def test_sends_the_candidates_in_the_prompt(
        self, candidates: list[TariffItem]
    ) -> None:
        classifier, messages = build_classifier([FakeResponse(make_proposal("85183001"))])

        await classifier.classify(build_extraction(), candidates)

        prompt = messages.requests[0]["messages"][0]["content"]
        for candidate in candidates:
            assert candidate.tariff_code in prompt


class TestCandidateGuardrail:
    async def test_retries_once_when_the_code_is_outside_the_list(
        self, candidates: list[TariffItem]
    ) -> None:
        classifier, messages = build_classifier(
            [
                FakeResponse(make_proposal("84713001")),  # not a candidate
                FakeResponse(make_proposal("85183001")),  # corrected
            ]
        )

        result = await classifier.classify(build_extraction(), candidates)

        assert result.tariff_code == "85183001"
        assert len(messages.requests) == 2

    async def test_the_retry_names_the_rejected_code(
        self, candidates: list[TariffItem]
    ) -> None:
        """A generic "try again" tends to reproduce the same wrong answer."""
        classifier, messages = build_classifier(
            [
                FakeResponse(make_proposal("84713001")),
                FakeResponse(make_proposal("85183001")),
            ]
        )

        await classifier.classify(build_extraction(), candidates)

        correction = messages.requests[1]["messages"][-1]["content"]
        assert "84713001" in correction
        assert "85183001" in correction

    async def test_gives_up_after_a_second_invalid_answer(
        self, candidates: list[TariffItem]
    ) -> None:
        classifier, messages = build_classifier(
            [
                FakeResponse(make_proposal("84713001")),
                FakeResponse(make_proposal("84716002")),
            ]
        )

        with pytest.raises(ClassificationOutOfCandidatesError):
            await classifier.classify(build_extraction(), candidates)

        assert len(messages.requests) == 2, "sólo se permite un reintento"


class TestNicoAlignment:
    async def test_corrects_a_nico_that_does_not_exist_for_the_code(
        self, candidates: list[TariffItem]
    ) -> None:
        classifier, _ = build_classifier([FakeResponse(make_proposal("85183001", nico="47"))])

        result = await classifier.classify(build_extraction(), candidates)

        assert result.nico == "00"

    async def test_keeps_a_valid_nico(self, candidates: list[TariffItem]) -> None:
        classifier, _ = build_classifier([FakeResponse(make_proposal("85183001", nico="00"))])

        result = await classifier.classify(build_extraction(), candidates)

        assert result.nico == "00"


class TestFailureModes:
    async def test_rejects_an_empty_candidate_list(self) -> None:
        classifier, _ = build_classifier([])

        with pytest.raises(LlmError, match="candidatas"):
            await classifier.classify(build_extraction(), [])

    async def test_reports_a_refusal(self, candidates: list[TariffItem]) -> None:
        classifier, _ = build_classifier([FakeResponse(None, stop_reason="refusal")])

        with pytest.raises(LlmError, match="declinó"):
            await classifier.classify(build_extraction(), candidates)

    async def test_reports_a_truncated_response(self, candidates: list[TariffItem]) -> None:
        classifier, _ = build_classifier([FakeResponse(None, stop_reason="max_tokens")])

        with pytest.raises(LlmError, match="truncó"):
            await classifier.classify(build_extraction(), candidates)
