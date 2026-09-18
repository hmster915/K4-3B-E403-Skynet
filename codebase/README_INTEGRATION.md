# Skynet Meeting Core — Hướng Dẫn Tích Hợp

Tài liệu hướng dẫn ngắn gọn và thực tế dành riêng cho Khoa để tích hợp core AI/STT vào Discord bot.

---

## 1. Module Này Làm Gì?

`skynet_core` nhận danh sách các file âm thanh WAV đã ghi âm từ Discord voice, chuyển thành văn bản bằng ElevenLabs STT (Speech-to-Text), gộp transcript và phân tích thành một biên bản cuộc họp có cấu trúc chuẩn xác (`MeetingReport`) thông qua LLM.

```text
WAV[]
  ↓
MeetingCore.process_wavs()
  ↓
Transcript
  ↓
MeetingReport
  ↓
MeetingCoreResult
```

---

## 2. Cài Đặt

Chạy lệnh sau từ thư mục gốc của repository:

```bash
pip install -e ./codebase
```

---

## 3. Các Biến Môi Trường Bắt Buộc

Cần cấu hình các biến sau trong file `.env` hoặc biến môi trường hệ thống trước khi khởi tạo `MeetingCore`:

```env
ELEVENLABS_API_KEY=your_elevenlabs_api_key
LLM_API_KEY=your_openai_or_compatible_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

Tùy chọn:
- `ELEVENLABS_BASE_URL` (mặc định: `https://api.elevenlabs.io`)

---

## 4. Code Mẫu Tích Hợp Tối Thiểu Cho Bot

```python
from pathlib import Path
from skynet_core import MeetingCore, MeetingCoreError

# 1. Khởi tạo core (dùng from_env để tự động đọc cấu hình)
core = MeetingCore.from_env()

# 2. Lấy danh sách đường dẫn file WAV từ audio sink sau khi record xong
wav_paths = [Path(p) for p in session.sink.audio_files.values()]

# 3. Xử lý bất đồng bộ (không block Discord event loop)
try:
    result = await core.process_wavs(wav_paths)
except MeetingCoreError as err:
    # Xử lý lỗi an toàn (thông báo cho kênh Discord, lỗi đã được lọc secret)
    print(f"Lỗi khi phân tích cuộc họp: {err}")
    return

# 4. Nhận transcript và biên bản cuộc họp đã phân tích
transcript = result.transcript
report = result.report
```

---

## 5. Cấu Trúc Kết Quả Trả Về

Hàm `core.process_wavs()` trả về đối tượng `MeetingCoreResult`:

```python
result.transcript.text  # Toàn bộ nội dung transcript đã gộp (str)

result.report.overview      # Tóm tắt tổng quan cuộc họp (str)
result.report.action_items  # Danh sách ActionItem (list[ActionItem])
result.report.sections      # Danh sách các mục chủ đề động (list[MeetingSection])
```

### Action Items (Đầu việc cần làm)

```python
for item in report.action_items:
    print(f"- Nhiệm vụ: {item.task}")
    print(f"  Người phụ trách: {item.owner}")     # str | None (nếu không nói rõ)
    print(f"  Hạn chót: {item.deadline}")         # str | None (nếu không nói rõ)
    print(f"  Bằng chứng: {item.evidence}")       # Trích dẫn trực tiếp từ transcript
```

### Sections & Points (Các phần chủ đề và ý chính)

```python
for section in report.sections:
    print(f"## {section.title}")
    for point in section.points:
        print(f"  * {point.content} (Trích dẫn: \"{point.evidence}\")")
```

---

## 6. Ranh Giới Trách Nhiệm

Ranh giới được phân định rõ ràng giữa Bot và Core:

| Thành phần | Trách nhiệm |
| :--- | :--- |
| **Khoa (Discord Bot)** | Kết nối Discord Voice, thu âm, giải mã Opus thành file WAV. |
| **Meeting Core** | Nhận file WAV $\rightarrow$ STT $\rightarrow$ gom Transcript $\rightarrow$ AI phân tích $\rightarrow$ trả về `MeetingReport`. |
| **Khoa (Discord Bot)** | Nhận `MeetingReport` $\rightarrow$ render lên Discord Embed / View / UI. |

---

## 7. Yêu Cầu Về Input

> [!IMPORTANT]
> **KHÔNG truyền đối tượng `RecordingSession`, Discord Member hay Guild vào `MeetingCore`.**
> `MeetingCore` chỉ nhận `Sequence[Path]` (danh sách đường dẫn file WAV PCM16 chuẩn: 16 kHz hoặc 48 kHz, mono hoặc stereo).

---

## 8. Ý Nghĩa Của Các Giá Trị `None`

Trong `ActionItem`:
- `owner = None`: Công việc đã được thống nhất làm, nhưng trong cuộc họp không chỉ định rõ ai làm.
- `deadline = None`: Hạn chót không được nhắc đến trong cuộc họp.

Không tự suy đoán hoặc gán mặc định nếu giá trị là `None`.

---

## 9. Render Section Động (Dynamic Sections)

Các section do LLM sinh ra là hoàn toàn động dựa theo chủ đề thực tế của cuộc họp. **Không** fix cứng tên các section (như `topics`, `decisions`, hay `open_questions`).

Hãy render lặp theo danh sách `report.sections`:

```python
for section in report.sections:
    embed.add_field(
        name=section.title,
        value="\n".join(f"• {p.content}" for p in section.points) or "N/A",
        inline=False,
    )
```

---

## 10. Giới Hạn & Lưu Ý Hiện Tại

- **Không phân tách người nói (Diarization) & Thứ tự thời gian (Chronology)**: Hiện tại văn bản STT từ các file WAV được nối với nhau đơn giản bằng ký tự xuống dòng `\n`. Không gắn tên người nói, Discord ID hay tái dựng timeline.
- **Chưa có EvidenceChecker / Revision Agent**: Phiên bản này trả về kết quả phân tích chuẩn lần đầu từ LLM, vòng lặp tự kiểm tra/sửa đổi (reflection loop) sẽ được bổ sung ở phase tiếp theo.
