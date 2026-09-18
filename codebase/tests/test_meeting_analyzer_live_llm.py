"""
Live LLM integration test for Phase 2 MeetingAnalyzer.

Reads configuration from codebase/.env:
- LLM_API_KEY   : API Key của provider (OpenAI, Gemini, Groq, MegaLLM, DeepSeek...)
- LLM_BASE_URL  : Base URL (mặc định: https://api.openai.com/v1)
- LLM_MODEL     : Tên model (ví dụ: gpt-4o-mini, gemini-2.0-flash, llama-3.3-70b...)

Có thể chạy bằng pytest:
    pytest codebase/tests/test_meeting_analyzer_live_llm.py -s

Hoặc chạy trực tiếp bằng python:
    python codebase/tests/test_meeting_analyzer_live_llm.py
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

from skynet_core.ai.meeting_analyzer import MeetingAnalyzer
from skynet_core.models.meeting import MeetingReport
from skynet_core.models.transcript import Transcript

# Nạp file .env từ codebase/.env hoặc thư mục hiện tại
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()


class LiveOpenAICompatibleGenerator:
    """Provider adapter cho bất kỳ LLM nào hỗ trợ chuẩn OpenAI chat completions:
    OpenAI, OpenRouter, Groq, Gemini (qua OpenAI endpoint), MegaLLM, DeepSeek, Ollama...
    """

    def __init__(
        self,
        api_key: str,
        base_url: str ,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        import httpx

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
        }

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.is_error:
                raise RuntimeError(
                    f"LLM Provider Error {response.status_code}: {response.text}"
                )
            data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"No choices returned from LLM provider: {data}")

        content = choices[0].get("message", {}).get("content", "")
        return content


@pytest.mark.skipif(
    not LLM_API_KEY,
    reason="Bỏ qua vì chưa cấu hình LLM_API_KEY trong file .env",
)
def test_live_llm_good_transcript() -> None:
    """Test gọi LLM thật với transcript rõ ràng."""
    transcript_text = (
        "Nam: Hôm nay mình chốt phần database nhé.\n"
        "Nam: Team sẽ dùng PostgreSQL.\n"
        "Nam: Chiến làm phần database trước thứ Sáu.\n"
        "Chiến: Ok, mình nhận.\n"
        "Khoa: Phần deploy để buổi sau bàn tiếp."
    )
    transcript = Transcript(text=transcript_text)

    generator = LiveOpenAICompatibleGenerator(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
    )
    analyzer = MeetingAnalyzer(text_generator=generator)

    report = analyzer.analyze(transcript)

    print("\n" + "=" * 50)
    print("KẾT QUẢ LLM THẬT - GOOD TRANSCRIPT:")
    print("=" * 50)
    print(report.model_dump_json(indent=2))

    assert isinstance(report, MeetingReport)
    assert len(report.overview) > 0
    assert len(report.action_items) >= 1
    assert any(item.owner == "Chiến" for item in report.action_items)


@pytest.mark.skipif(
    not LLM_API_KEY,
    reason="Bỏ qua vì chưa cấu hình LLM_API_KEY trong file .env",
)
def test_live_llm_noisy_transcript() -> None:
    """Test gọi LLM thật với transcript nhiễu, quảng cáo và thông tin xung đột."""
    noisy_transcript_text = (
        "Nam: Khoa làm phần deploy nhé.\n"
        "Chiến: Hình như... deploy... Chiến làm thì phải.\n"
        "ừm... cái data... lalaschool... thứ sáu...\n"
        "Các bạn hãy đăng ký kênh LaLaSchool để không bỏ lỡ video.\n"
        "Nam: Deadline thì chưa chốt."
    )
    transcript = Transcript(text=noisy_transcript_text)

    generator = LiveOpenAICompatibleGenerator(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
    )
    analyzer = MeetingAnalyzer(text_generator=generator)

    report = analyzer.analyze(transcript)

    print("\n" + "=" * 50)
    print("KẾT QUẢ LLM THẬT - NOISY TRANSCRIPT:")
    print("=" * 50)
    print(report.model_dump_json(indent=2))

    assert isinstance(report, MeetingReport)
    # Không được nhận vơ quảng cáo làm action item
    for item in report.action_items:
        assert "lalaschool" not in item.task.lower()
        assert "đăng ký" not in item.task.lower()


if __name__ == "__main__":
    if not LLM_API_KEY:
        print("Vui lòng điền LLM_API_KEY vào file codebase/.env trước khi chạy!")
        exit(1)

    print(f"Đang kết nối LLM: {LLM_MODEL} tại {LLM_BASE_URL}...")
    print("\n--- TEST 1: GOOD TRANSCRIPT ---")
    test_live_llm_good_transcript()

    print("\n--- TEST 2: NOISY TRANSCRIPT ---")
    test_live_llm_noisy_transcript()
    print("\nHoàn tất test LLM thật!")
