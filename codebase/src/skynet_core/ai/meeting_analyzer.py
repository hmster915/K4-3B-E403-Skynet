"""
analyze()            --> transcript -> MeetingReport
_build_user_prompt() --> build transcript prompt
_clean_json_text()   --> strip optional markdown code fences
_parse_response()    --> JSON -> MeetingReport
"""

import json

from pydantic import ValidationError

from skynet_core.models.meeting import MeetingReport
from skynet_core.models.transcript import Transcript
from skynet_core.providers.text.base import TextGenerator

SYSTEM_PROMPT = """

You are a meeting-note analyzer.

From the transcript, create a concise structured meeting report.

Rules:
- Use only information supported by the transcript. Never guess or use outside knowledge.
- Always produce: overview and action_items.
- After them, create only useful topic sections that reflect what was actually discussed.
- Action item = an explicit assignment, commitment, or agreed next step; not a suggestion, filler, repeated phrase, advertisement, or ASR noise.
- For action items, owner and deadline must be null if not explicitly stated.
- If information is missing, do not fill it in.
- If information is ambiguous, do not resolve it by assumption.
- If the transcript contains conflicting statements, preserve the conflict instead of choosing one as true.
- If an important point is incomplete, ambiguous, or conflicting, place it in a "Needs Confirmation" section.
- If text appears corrupted, meaningless, or caused by transcription noise, ignore it unless it materially affects the meeting outcome.
- Do not silently correct names, numbers, dates, technical terms, or factual claims.
- Keep the overview limited to reliable, supported information.
- Keep each point concise.
- Attach a short exact transcript evidence to every action item and section point.
- If the transcript contains too little reliable information, return a minimal report instead of inventing content.
- Return valid JSON only.
"""


class MeetingAnalysisError(RuntimeError):
    """Raised when meeting analysis fails due to provider errors, invalid JSON, or schema violations."""


class MeetingAnalyzer:
    """Analyzes transcripts to produce validated structured meeting reports."""

    # Preflight: Role=Initialize MeetingAnalyzer | Input=TextGenerator instance | Output=MeetingAnalyzer | Decision boundary=Dependency injection only | Failure/Test=Invalid provider reference
    def __init__(
        self,
        text_generator: TextGenerator,
    ) -> None:
        self._text_generator = text_generator

    # Preflight: Role=Analyze meeting transcript | Input=Transcript | Output=MeetingReport | Decision boundary=Prompt generation and error wrapping only | Failure/Test=MeetingAnalysisError on failure
    def analyze(
        self,
        transcript: Transcript,
    ) -> MeetingReport:
        user_prompt = self._build_user_prompt(transcript.text)

        try:
            raw_response = self._text_generator.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception as err:
            raise MeetingAnalysisError(
                f"Text generator provider failed: {err}"
            ) from err

        return self._parse_response(raw_response)

    # Preflight: Role=Build formatted user prompt | Input=transcript text str | Output=formatted user prompt str | Decision boundary=Prompt template formatting only | Failure/Test=Deterministic formatting
    def _build_user_prompt(
        self,
        transcript_text: str,
    ) -> str:
        return (
            "Analyze the following meeting transcript.\n\n"
            f"<transcript>\n{transcript_text}\n</transcript>\n\n"
            "Return only the JSON report matching this exact structure:\n"
            "{\n"
            '  "overview": "Short summary of main meeting contents and goals",\n'
            '  "action_items": [\n'
            "    {\n"
            '      "task": "Task description",\n'
            '      "owner": "Person name or null",\n'
            '      "deadline": "Deadline or null",\n'
            '      "evidence": "Direct quote from transcript"\n'
            "    }\n"
            "  ],\n"
            '  "sections": [\n'
            "    {\n"
            '      "title": "Section title",\n'
            '      "points": [\n'
            "        {\n"
            '          "content": "Main point",\n'
            '          "evidence": "Direct quote from transcript"\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}"
        )

    # Preflight: Role=Clean markdown fences from LLM text | Input=raw text str | Output=cleaned JSON text str | Decision boundary=Strip markdown markers if present | Failure/Test=Deterministic string cleanup
    def _clean_json_text(
        self,
        text: str,
    ) -> str:
        cleaned = text.strip()
        if not cleaned.startswith("```"):
            return cleaned

        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    # Preflight: Role=Parse and validate LLM output | Input=raw JSON string | Output=validated MeetingReport | Decision boundary=JSON deserialization and strict Pydantic validation | Failure/Test=MeetingAnalysisError on invalid JSON or schema violation
    def _parse_response(
        self,
        raw_response: str,
    ) -> MeetingReport:
        cleaned = self._clean_json_text(raw_response)

        try:
            data = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as err:
            raise MeetingAnalysisError(
                f"Failed to parse LLM response as JSON: {err}"
            ) from err

        if not isinstance(data, dict):
            raise MeetingAnalysisError(
                "LLM response violated schema: expected JSON object"
            )

        try:
            return MeetingReport.model_validate(data)
        except ValidationError as err:
            raise MeetingAnalysisError(
                f"LLM response violated schema: {err}"
            ) from err
