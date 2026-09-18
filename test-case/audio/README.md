# Audio fixtures

Các fixture được tham chiếu trong `../test-case.json`.

## Fixture WAV end-to-end

`T01`–`T11` là WAV tổng hợp hoặc đã được phép sử dụng, đọc đúng `reference_transcript` của case tương ứng.

- WAV phải là PCM 16-bit không nén, mono hoặc stereo, 16 kHz hoặc 48 kHz, và có ít nhất một audio frame.
- `T01` dùng hai file: `T01-speaker-1.wav` và `T01-speaker-2.wav`.
- Không dùng audio, tên, hoặc thông tin của người thật trong repository public.

## Fixture kiểm tra lỗi format

- `T12-24bit.wav`: WAV không rỗng nhưng PCM 24-bit.
- `T13-empty.wav`: WAV PCM16 không có audio frame.
- `T15-silence.wav`, `T16.wav`, `T17.wav`, `T18.wav`, `T19.wav`: chỉ là path đầu vào cho test có STT/LLM stub.
- `T20-raw-discord.opus`: raw Discord Opus để xác minh pipeline từ chối file không phải WAV.

Các case có `provider_stub` hoặc `llm_stub` không gọi API thật; chúng đo cách `MeetingCore` bọc và báo lỗi.
