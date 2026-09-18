"""
Tests for Phase 2: Meeting Note Analyzer.

Deterministic tests using FakeTextGenerator to verify:
- System prompt anti-guess rules and user prompt composition
- Output JSON contract and strict Pydantic schema validation
- Handling of good transcripts
- Handling of bad / noisy transcripts (no hallucinations, needs confirmation section)
- Failure cases: non-JSON output, schema violation, provider failure
"""

import json
import pytest

from skynet_core.ai.meeting_analyzer import (
    SYSTEM_PROMPT,
    MeetingAnalysisError,
    MeetingAnalyzer,
)
from skynet_core.models.meeting import (
    ActionItem,
    MeetingPoint,
    MeetingReport,
    MeetingSection,
)
from skynet_core.models.transcript import Transcript
from skynet_core.providers.text.base import TextGenerator


class FakeTextGenerator:
    """Deterministic stub text generator capturing prompts and returning configured responses."""

    def __init__(
        self,
        response: str = "",
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.captured_system_prompt: str | None = None
        self.captured_user_prompt: str | None = None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self.captured_system_prompt = system_prompt
        self.captured_user_prompt = user_prompt
        if self.error is not None:
            raise self.error
        return self.response


# ---------------------------------------------------------------------------
# Test Case 1: Good Transcript
# ---------------------------------------------------------------------------


def test_analyze_good_transcript() -> None:
    """Test Case 1: Valid transcript produces a well-formed MeetingReport."""
    transcript_text = (
        "Nam: Hôm nay mình chốt phần database nhé.\n"
        "Nam: Team sẽ dùng PostgreSQL.\n"
        "Nam: Chiến làm phần database trước thứ Sáu.\n"
        "Chiến: Ok, mình nhận.\n"
        "Khoa: Phần deploy để buổi sau bàn tiếp."
    )
    transcript = Transcript(text=transcript_text)

    llm_payload = {
        "overview": "Team đã thảo luận và thống nhất dùng PostgreSQL cho database. Chiến nhận làm database trước thứ Sáu, còn phần deploy hoãn lại bàn sau.",
        "action_items": [
            {
                "task": "Làm phần database",
                "owner": "Chiến",
                "deadline": "thứ Sáu",
                "evidence": "Chiến làm phần database trước thứ Sáu.",
            }
        ],
        "sections": [
            {
                "title": "Database",
                "points": [
                    {
                        "content": "Team quyết định sử dụng PostgreSQL.",
                        "evidence": "Team sẽ dùng PostgreSQL.",
                    }
                ],
            },
            {
                "title": "Deployment",
                "points": [
                    {
                        "content": "Phần deploy để buổi sau bàn tiếp.",
                        "evidence": "Khoa: Phần deploy để buổi sau bàn tiếp.",
                    }
                ],
            },
        ],
    }

    generator = FakeTextGenerator(response=json.dumps(llm_payload))
    analyzer = MeetingAnalyzer(text_generator=generator)

    report = analyzer.analyze(transcript)

    # 1. Result type
    assert isinstance(report, MeetingReport)

    # 2. Action items verification
    assert len(report.action_items) == 1
    action = report.action_items[0]
    assert isinstance(action, ActionItem)
    assert action.task == "Làm phần database"
    assert action.owner == "Chiến"
    assert action.deadline == "thứ Sáu"
    assert action.evidence == "Chiến làm phần database trước thứ Sáu."

    # 3. Dynamic sections
    assert len(report.sections) == 2
    assert report.sections[0].title == "Database"
    assert report.sections[0].points[0].content == "Team quyết định sử dụng PostgreSQL."
    assert report.sections[0].points[0].evidence == "Team sẽ dùng PostgreSQL."

    # 4. System prompt checks (anti-guess, action item criteria)
    assert generator.captured_system_prompt is not None
    assert generator.captured_system_prompt == SYSTEM_PROMPT
    assert "Never guess or use outside knowledge" in generator.captured_system_prompt
    assert "action item = an explicit assignment" in generator.captured_system_prompt.lower()

    # 5. User prompt checks
    assert generator.captured_user_prompt is not None
    assert transcript_text in generator.captured_user_prompt
    assert "<transcript>" in generator.captured_user_prompt


# ---------------------------------------------------------------------------
# Test Case 2: Bad / Noisy Transcript
# ---------------------------------------------------------------------------


def test_analyze_bad_noisy_transcript() -> None:
    """Test Case 2: Noisy transcript with conflicts and ads does not hallucinate facts."""
    noisy_transcript_text = (
        "Nam: Khoa làm phần deploy nhé.\n"
        "Chiến: Hình như... deploy... Chiến làm thì phải.\n"
        "ừm... cái data... lalaschool... thứ sáu...\n"
        "Các bạn hãy đăng ký kênh LaLaSchool để không bỏ lỡ video.\n"
        "Nam: Deadline thì chưa chốt."
    )
    transcript = Transcript(text=noisy_transcript_text)

    llm_payload = {
        "overview": "Cuộc họp trao đổi về việc phụ trách deploy nhưng chưa thống nhất người làm và deadline chưa chốt.",
        "action_items": [],
        "sections": [
            {
                "title": "Needs Confirmation",
                "points": [
                    {
                        "content": "Người phụ trách phần deploy chưa rõ ràng giữa Khoa và Chiến.",
                        "evidence": "Khoa làm phần deploy nhé. / Hình như... deploy... Chiến làm thì phải.",
                    },
                    {
                        "content": "Deadline chưa được chốt.",
                        "evidence": "Nam: Deadline thì chưa chốt.",
                    },
                ],
            }
        ],
    }

    generator = FakeTextGenerator(response=json.dumps(llm_payload))
    analyzer = MeetingAnalyzer(text_generator=generator)

    report = analyzer.analyze(transcript)

    # 1. Report validates
    assert isinstance(report, MeetingReport)

    # 2. No invented deadline or fake action item from advertisement
    for item in report.action_items:
        assert item.deadline is None
        assert "lalaschool" not in item.task.lower()
        assert "đăng ký" not in item.task.lower()

    # 3. Needs Confirmation section is present and holds conflicting points
    needs_confirmation_sections = [
        s for s in report.sections if s.title.strip().lower() == "needs confirmation"
    ]
    assert len(needs_confirmation_sections) == 1
    nc_section = needs_confirmation_sections[0]
    assert len(nc_section.points) >= 1

    # 4. Evidence preserved
    for pt in nc_section.points:
        assert bool(pt.evidence)


# ---------------------------------------------------------------------------
# Test Case 3: Invalid LLM Output & Error Handling
# ---------------------------------------------------------------------------


def test_analyze_fails_on_invalid_json() -> None:
    """Test Case 3: Non-JSON LLM output raises MeetingAnalysisError."""
    transcript = Transcript(text="Nam: Xin chào mọi người.")
    generator = FakeTextGenerator(response="not-json")
    analyzer = MeetingAnalyzer(text_generator=generator)

    with pytest.raises(MeetingAnalysisError, match="Failed to parse LLM response as JSON"):
        analyzer.analyze(transcript)


def test_analyze_fails_on_schema_violation_missing_fields() -> None:
    """Schema failure when required fields (like action_items) are missing."""
    transcript = Transcript(text="Nam: Xin chào mọi người.")
    generator = FakeTextGenerator(response=json.dumps({"overview": "Chỉ có overview"}))
    analyzer = MeetingAnalyzer(text_generator=generator)

    with pytest.raises(MeetingAnalysisError, match="violated schema"):
        analyzer.analyze(transcript)


def test_analyze_fails_on_forbidden_extra_fields() -> None:
    """Schema failure when unknown fields are injected violating FrozenModel extra='forbid'."""
    transcript = Transcript(text="Nam: Xin chào mọi người.")
    payload = {
        "overview": "Tổng quan",
        "action_items": [],
        "sections": [],
        "unauthorized_field": "injected value",
    }
    generator = FakeTextGenerator(response=json.dumps(payload))
    analyzer = MeetingAnalyzer(text_generator=generator)

    with pytest.raises(MeetingAnalysisError, match="violated schema"):
        analyzer.analyze(transcript)


def test_analyze_fails_on_provider_error() -> None:
    """Provider failure during generate() raises wrapped MeetingAnalysisError."""
    transcript = Transcript(text="Nam: Xin chào mọi người.")
    generator = FakeTextGenerator(error=RuntimeError("Connection refused by provider"))
    analyzer = MeetingAnalyzer(text_generator=generator)

    with pytest.raises(MeetingAnalysisError, match="Text generator provider failed"):
        analyzer.analyze(transcript)


def test_analyze_strips_markdown_code_fences() -> None:
    """LLM outputs wrapped in ```json ... ``` code fences are cleanly handled."""
    transcript = Transcript(text="Nam: Xin chào mọi người.")
    payload = {
        "overview": "Cuộc họp chào hỏi ngắn.",
        "action_items": [],
        "sections": [],
    }
    markdown_wrapped = f"```json\n{json.dumps(payload)}\n```"
    generator = FakeTextGenerator(response=markdown_wrapped)
    analyzer = MeetingAnalyzer(text_generator=generator)

    report = analyzer.analyze(transcript)
    assert isinstance(report, MeetingReport)
    assert report.overview == "Cuộc họp chào hỏi ngắn."
