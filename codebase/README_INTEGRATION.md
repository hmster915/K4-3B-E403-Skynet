# Skynet Core — Tích hợp vào Bot Khoa

## 1. Vị trí thư mục

Lấy nguyên thư mục `codebase/` từ nhánh `chien` và đặt tại root repo của Khoa.

.env 
"""
ELEVENLABS_API_KEY=
ELEVENLABS_BASE_URL=https://api.elevenlabs.io

# Part 2
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
"""


Cấu trúc cần có:

K4-3B-E403-Skynet/
├── bot/
├── backend/
├── codebase/
│   ├── pyproject.toml
│   ├── src/skynet_core/
│   └── tests/
└── run.py

Không đặt `codebase/` bên trong `bot/`.

Cài core từ root project:

```bash
pip install -e ./codebase

"""
sửa code 2. Các file Khoa cần sửa
bot/commands/recording.py

Bỏ việc khởi tạo:

TranscriptionService(mode="mock")
SummarizationService(mode="mock")

Khởi tạo một lần:

from skynet_core import MeetingCore

self.meeting_core = MeetingCore.from_env()

Phần Discord recording /record, /end-record giữ nguyên.

Phần render kết quả đổi sang đọc:

result.report.overview
result.report.action_items
result.report.sections
bot/services/meeting_processing_service.py

Đây là điểm nối chính với core.

Lấy WAV từ:

wav_paths = list(session.sink.audio_files.values())

Sau đó gọi:

result = await meeting_core.process_wavs(wav_paths)

Không tự gọi STT hoặc LLM trong service này nữa.

bot/models/meeting.py

Không duy trì schema MeetingSummary riêng cho AI result.

Dùng MeetingReport do skynet_core trả về.

Có thể giữ model riêng của Khoa cho personal_notes và dữ liệu Discord.
"""

xóa 2 thư mục : 
bot/services/transcription_service.py và
bot/services/summarization_service.py


pytest codebase/tests/test_meeting_core.py -v