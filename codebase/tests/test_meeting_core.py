"""
Offline tests for MeetingCore public façade.

Verifies end-to-end orchestration without real network calls using:
FakeAudioProvider + FakeTextGenerator + real MeetingAnalyzer + real MeetingCore.
"""

import json
from pathlib import Path
import pytest

from skynet_core import (
    MeetingCore,
    MeetingCoreError,
    MeetingCoreResult,
)
from skynet_core.ai.meeting_analyzer import MeetingAnalyzer
from skynet_core.models.meeting import MeetingReport
from skynet_core.models.transcript import Transcript


class FakeAudioProvider:
    """Offline stub for AudioProvider protocol."""

    def __init__(
        self,
        transcripts: dict[Path, str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.transcripts = transcripts or {}
        self.error = error
        self.transcribed_paths: list[Path] = []

    async def transcribe_wav(self, wav_path: Path) -> Transcript:
        self.transcribed_paths.append(wav_path)
        if self.error is not None:
            raise self.error
        text = self.transcripts.get(wav_path, "")
        return Transcript(text=text if text else "dummy")


class BlankFakeAudioProvider:
    """Offline stub returning empty/whitespace transcripts."""

    def __init__(self, blank_text: str = "   \n\t  ") -> None:
        self.blank_text = blank_text
        self.transcribed_paths: list[Path] = []

    async def transcribe_wav(self, wav_path: Path) -> Transcript:
        self.transcribed_paths.append(wav_path)
        # Note: Transcript requires min_length=1, so we return whitespace
        return Transcript(text=self.blank_text)


class FakeTextGenerator:
    """Offline stub for TextGenerator protocol capturing prompts."""

    def __init__(
        self,
        response: str = "",
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.call_count = 0
        self.captured_system_prompt: str | None = None
        self.captured_user_prompt: str | None = None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.call_count += 1
        self.captured_system_prompt = system_prompt
        self.captured_user_prompt = user_prompt
        if self.error is not None:
            raise self.error
        return self.response


VALID_REPORT_JSON = json.dumps(
    {
        "overview": "Team bàn về database và thống nhất phân công công việc.",
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
                        "content": "Team thảo luận phần database",
                        "evidence": "Hôm nay team bàn phần database.",
                    }
                ],
            }
        ],
    }
)


# ---------------------------------------------------------------------------
# CASE 1 — MULTIPLE WAV FILES
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_process_wavs_multiple_files() -> None:
    wav1 = Path("speaker_1.wav")
    wav2 = Path("speaker_2.wav")

    fake_audio = FakeAudioProvider(
        transcripts={
            wav1: "Hôm nay team bàn phần database.",
            wav2: "Chiến làm phần database trước thứ Sáu.",
        }
    )
    fake_llm = FakeTextGenerator(response=VALID_REPORT_JSON)
    analyzer = MeetingAnalyzer(text_generator=fake_llm)
    core = MeetingCore(audio_provider=fake_audio, meeting_analyzer=analyzer)

    result = await core.process_wavs([wav1, wav2])

    # Assert contract
    assert isinstance(result, MeetingCoreResult)
    assert isinstance(result.transcript, Transcript)
    expected_transcript = (
        "Hôm nay team bàn phần database.\n"
        "Chiến làm phần database trước thứ Sáu."
    )
    assert result.transcript.text == expected_transcript

    # Assert no speaker names or timestamps were injected
    assert "speaker_1" not in result.transcript.text
    assert "Speaker 1" not in result.transcript.text
    assert "Discord" not in result.transcript.text

    # Assert report structure
    assert isinstance(result.report, MeetingReport)
    assert len(result.report.action_items) == 1
    assert result.report.action_items[0].task == "Làm phần database"
    assert result.report.action_items[0].owner == "Chiến"
    assert result.report.action_items[0].deadline == "thứ Sáu"
    assert (
        result.report.action_items[0].evidence
        == "Chiến làm phần database trước thứ Sáu."
    )
    assert fake_llm.call_count == 1


# ---------------------------------------------------------------------------
# CASE 2 — ONE WAV FILE
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_process_wavs_single_file() -> None:
    wav = Path("speaker_single.wav")
    fake_audio = FakeAudioProvider(
        transcripts={
            wav: "Team thống nhất sử dụng PostgreSQL.",
        }
    )
    report_json = json.dumps(
        {
            "overview": "Team thống nhất sử dụng PostgreSQL cho hệ thống.",
            "action_items": [],
            "sections": [
                {
                    "title": "Công nghệ",
                    "points": [
                        {
                            "content": "Sử dụng PostgreSQL",
                            "evidence": "Team thống nhất sử dụng PostgreSQL.",
                        }
                    ],
                }
            ],
        }
    )
    fake_llm = FakeTextGenerator(response=report_json)
    analyzer = MeetingAnalyzer(text_generator=fake_llm)
    core = MeetingCore(audio_provider=fake_audio, meeting_analyzer=analyzer)

    result = await core.process_wavs([wav])

    assert isinstance(result, MeetingCoreResult)
    assert result.transcript.text == "Team thống nhất sử dụng PostgreSQL."
    assert isinstance(result.report, MeetingReport)
    assert result.report.overview == "Team thống nhất sử dụng PostgreSQL cho hệ thống."
    assert len(result.report.sections) == 1
    assert fake_llm.call_count == 1


# ---------------------------------------------------------------------------
# CASE 3 — EMPTY INPUT
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_process_wavs_empty_input_raises_error() -> None:
    fake_audio = FakeAudioProvider()
    fake_llm = FakeTextGenerator(response=VALID_REPORT_JSON)
    analyzer = MeetingAnalyzer(text_generator=fake_llm)
    core = MeetingCore(audio_provider=fake_audio, meeting_analyzer=analyzer)

    with pytest.raises(MeetingCoreError, match="No WAV files provided"):
        await core.process_wavs([])

    assert fake_llm.call_count == 0


# ---------------------------------------------------------------------------
# CASE 4 — NO USEFUL TRANSCRIPT
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_process_wavs_no_useful_transcript_raises_error() -> None:
    wav1 = Path("silent1.wav")
    wav2 = Path("silent2.wav")

    fake_audio = BlankFakeAudioProvider(blank_text="   \n  \t ")
    fake_llm = FakeTextGenerator(response=VALID_REPORT_JSON)
    analyzer = MeetingAnalyzer(text_generator=fake_llm)
    core = MeetingCore(audio_provider=fake_audio, meeting_analyzer=analyzer)

    with pytest.raises(MeetingCoreError, match="No usable transcript produced"):
        await core.process_wavs([wav1, wav2])

    # MeetingAnalyzer must not be called when transcripts are unusable
    assert fake_llm.call_count == 0


# ---------------------------------------------------------------------------
# CASE 5 — STT FAILURE
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_process_wavs_stt_failure_raises_error() -> None:
    wav = Path("corrupted.wav")
    fake_audio = FakeAudioProvider(
        error=RuntimeError("Secret_Token_12345: WebSocket handshake failed")
    )
    fake_llm = FakeTextGenerator(response=VALID_REPORT_JSON)
    analyzer = MeetingAnalyzer(text_generator=fake_llm)
    core = MeetingCore(audio_provider=fake_audio, meeting_analyzer=analyzer)

    with pytest.raises(MeetingCoreError) as exc_info:
        await core.process_wavs([wav])

    # Error message must be sanitized: no leaked credentials
    error_msg = str(exc_info.value)
    assert "Secret_Token_12345" not in error_msg
    assert fake_llm.call_count == 0


# ---------------------------------------------------------------------------
# CASE 6 — ANALYZER FAILURE
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_process_wavs_analyzer_invalid_json_raises_error() -> None:
    wav = Path("speaker.wav")
    fake_audio = FakeAudioProvider(
        transcripts={wav: "Hôm nay họp về backend."}
    )
    fake_llm = FakeTextGenerator(response="not a valid json response")
    analyzer = MeetingAnalyzer(text_generator=fake_llm)
    core = MeetingCore(audio_provider=fake_audio, meeting_analyzer=analyzer)

    with pytest.raises(MeetingCoreError, match="Meeting analysis failed"):
        await core.process_wavs([wav])


@pytest.mark.anyio
async def test_process_wavs_analyzer_provider_failure_raises_error() -> None:
    wav = Path("speaker.wav")
    fake_audio = FakeAudioProvider(
        transcripts={wav: "Hôm nay họp về backend."}
    )
    fake_llm = FakeTextGenerator(error=RuntimeError("OpenAI API unreachable"))
    analyzer = MeetingAnalyzer(text_generator=fake_llm)
    core = MeetingCore(audio_provider=fake_audio, meeting_analyzer=analyzer)

    with pytest.raises(MeetingCoreError, match="Meeting analysis failed"):
        await core.process_wavs([wav])


# ---------------------------------------------------------------------------
# CASE 7 — MeetingCore.from_env() CONFIGURATION VALIDATION
# ---------------------------------------------------------------------------


def test_from_env_missing_keys_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    with pytest.raises(MeetingCoreError):
        MeetingCore.from_env()


def test_from_env_success_creates_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test_elevenlabs_key")
    monkeypatch.setenv("LLM_API_KEY", "test_llm_key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")

    core = MeetingCore.from_env()
    assert isinstance(core, MeetingCore)


# ---------------------------------------------------------------------------
# CASE 8 — OpenAICompatibleTextGenerator ADAPTER TESTS
# ---------------------------------------------------------------------------


def test_openai_compatible_generator_validation() -> None:
    from skynet_core.providers.text.openai_compatible import (
        OpenAICompatibleTextGenerator,
    )

    with pytest.raises(ValueError, match="api_key is required"):
        OpenAICompatibleTextGenerator(api_key="", base_url="http://x", model="m")

    with pytest.raises(ValueError, match="base_url is required"):
        OpenAICompatibleTextGenerator(api_key="k", base_url="", model="m")

    with pytest.raises(ValueError, match="model is required"):
        OpenAICompatibleTextGenerator(api_key="k", base_url="http://x", model="")


def test_openai_compatible_generator_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx
    from skynet_core.providers.text.openai_compatible import (
        OpenAICompatibleTextGenerator,
    )

    def fake_post(self: httpx.Client, url: str, **kwargs: object) -> httpx.Response:
        content = json.dumps(
            {"choices": [{"message": {"content": '{"overview": "mocked"}'}}]}
        ).encode("utf-8")
        return httpx.Response(status_code=200, content=content)

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    gen = OpenAICompatibleTextGenerator(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
    )
    res = gen.generate(system_prompt="sys", user_prompt="usr")
    assert res == '{"overview": "mocked"}'


def test_openai_compatible_generator_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx
    from skynet_core.providers.text.openai_compatible import (
        OpenAICompatibleTextGenerator,
    )

    def fake_post_err(self: httpx.Client, url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(
            status_code=401,
            content=b'{"error": "invalid_api_key"}',
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post_err)

    gen = OpenAICompatibleTextGenerator(
        api_key="sk-bad",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
    )
    with pytest.raises(RuntimeError, match="HTTP error 401"):
        gen.generate(system_prompt="sys", user_prompt="usr")


def test_openai_compatible_generator_missing_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx
    from skynet_core.providers.text.openai_compatible import (
        OpenAICompatibleTextGenerator,
    )

    def fake_post_empty(self: httpx.Client, url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(status_code=200, content=b'{"choices": []}')

    monkeypatch.setattr(httpx.Client, "post", fake_post_empty)

    gen = OpenAICompatibleTextGenerator(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
    )
    with pytest.raises(RuntimeError, match="missing 'choices'"):
        gen.generate(system_prompt="sys", user_prompt="usr")
