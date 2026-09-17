# CP2 — STRUCTURE C  
## Trợ lý Kute · Meeting Mode → AI Draft → Human Confirmation

> **Mục tiêu:** mô tả rõ luồng hoạt động của tính năng Meeting Mode và chỉ ra chính xác bước nào **AI tham gia / AI quyết định / người dùng xác nhận**.  
> **Nguyên tắc:** AI chỉ điền thông tin khi có căn cứ trong cuộc họp. Nếu chưa đủ căn cứ → đánh dấu **CHƯA XÁC ĐỊNH / NEED CONFIRMATION**.

---

```text
MEETING INTELLIGENCE / STRUCTURE C
capture the meeting → understand what matters → verify uncertainty → human confirms → publish

LEGEND
[ SYSTEM ]  logic / storage / Discord integration
[ AI ]      model participates
< AI ? >    AI makes a decision
[ HUMAN ]   user reviews / confirms


── 01 / CAPTURE ──────────────────────────────────────────────────────────────────────────────────

        DISCORD / REAL MEETING                            MEETING INPUT

        ┌─────────────────────────┐                      ┌─────────────────────────┐
        │      START MEETING      │                      │     AUDIO / TRANSCRIPT  │
        │                         │                      │                         │
        │  /meeting start         │ ───────────────────► │  voice / file / text    │
        │  or upload recording    │                      │  meeting context        │
        └─────────────────────────┘                      └────────────┬────────────┘
                                                                    │
                                                                    │
                                                             [ SYSTEM ]
                                                                    │
                                                                    ▼


── 02 / TRANSCRIBE + PREPARE ─────────────────────────────────────────────────────────────────────

                                                       ┌─────────────────────────┐
                                                       │     SPEECH TO TEXT      │
                                                       │          [ AI ]         │
                                                       │                         │
                                                       │ audio → transcript      │
                                                       │ preserve timestamps     │
                                                       └────────────┬────────────┘
                                                                    │
                                                                    ▼
                                                       ┌─────────────────────────┐
                                                       │    CLEAN TRANSCRIPT     │
                                                       │       [ SYSTEM ]        │
                                                       │                         │
                                                       │ chunks / timestamps     │
                                                       │ meeting metadata        │
                                                       └────────────┬────────────┘
                                                                    │
                                                                    ▼


── 03 / UNDERSTAND ────────────────────────────────────────────────────────────────────────────────

        AI GATHERS                                     AI EXTRACTS CANDIDATES

        transcript                                     ┌───────────────────────────────┐
        meeting context                                │   MEETING UNDERSTANDING       │
        timestamps             ──────────────────────► │            [ AI ]             │
                                                       │                               │
                                                       │  • Summary                    │
                                                       │  • Decisions                  │
                                                       │  • Action Items               │
                                                       │  • Owner                      │
                                                       │  • Deadline                   │
                                                       │  • Open Questions             │
                                                       └──────────────┬────────────────┘
                                                                      │
                                                                      ▼


── 04 / AI DECISION ───────────────────────────────────────────────────────────────────────────────

                                               ┌────────────────────────────────┐
                                               │  < AI ? > ENOUGH EVIDENCE ?    │
                                               │                                │
                                               │  Is the information explicitly │
                                               │  supported by the transcript?  │
                                               └───────────────┬────────────────┘
                                                               │
                                    ┌──────────────────────────┴──────────────────────────┐
                                    │                                                     │
                                   YES                                                    NO
                                    │                                                     │
                                    ▼                                                     ▼

                    ┌───────────────────────────┐                         ┌───────────────────────────┐
                    │     EXTRACT VALUE         │                         │    NEED CONFIRMATION      │
                    │          [ AI ]           │                         │          [ AI ]           │
                    │                           │                         │                           │
                    │ Owner = Khoa              │                         │ Owner = chưa xác định     │
                    │ Deadline = 21:00          │                         │ Deadline = chưa xác định  │
                    │ Action = Build API        │                         │ Flag uncertain fields     │
                    └─────────────┬─────────────┘                         └─────────────┬─────────────┘
                                  │                                                     │
                                  └──────────────────────────┬──────────────────────────┘
                                                             │
                                                             ▼


── 05 / CREATE DRAFT ───────────────────────────────────────────────────────────────────────────────

                                                       ┌───────────────────────────────┐
                                                       │     DRAFT MEETING NOTE        │
                                                       │            [ AI ]             │
                                                       │                               │
                                                       │  SUMMARY                      │
                                                       │  DECISIONS                    │
                                                       │  ACTION ITEMS                 │
                                                       │  OWNER / DEADLINE             │
                                                       │  OPEN QUESTIONS               │
                                                       │  NEED CONFIRMATION            │
                                                       └──────────────┬────────────────┘
                                                                      │
                                                                      ▼


── 06 / HUMAN REVIEW ───────────────────────────────────────────────────────────────────────────────

        YOU / REVIEW

        ┌─────────────────────────────────────────────────────────────────────────────────────────┐
        │                                  [ HUMAN ]                                              │
        │                                                                                         │
        │   [✓] confirm item      [ edit ] correct owner/deadline      [x] reject wrong item      │
        │                                                                                         │
        │   AI draft is NOT final until the user has a chance to verify uncertain information.   │
        └───────────────────────────────────────────────┬─────────────────────────────────────────┘
                                                        │
                                         ┌──────────────┴──────────────┐
                                         │                             │
                                      APPROVE                        EDIT
                                         │                             │
                                         │                             └──────────────┐
                                         │                                            │
                                         ▼                                            │
                                                                                      │
                                                                              revise / confirm
                                                                                      │
                                         ┌────────────────────────────────────────────┘
                                         │
                                         ▼


── 07 / PUBLISH ───────────────────────────────────────────────────────────────────────────────────

                                                       ┌───────────────────────────────┐
                                                       │       POST TO DISCORD         │
                                                       │          [ SYSTEM ]           │
                                                       │                               │
                                                       │ #meeting-summary              │
                                                       │ thread / channel              │
                                                       └──────────────┬────────────────┘
                                                                      │
                                                                      ▼

        FINAL OUTPUT

        ┌─────────────────────────────────────────────────────────────────────────────────────────┐
        │ 📌 MEETING SUMMARY                                                                     │
        │                                                                                         │
        │ Summary        — nội dung chính                                                         │
        │ Decisions      — những gì đã được chốt                                                  │
        │ Action Items   — việc cần làm                                                           │
        │ Owner          — người phụ trách                                                        │
        │ Deadline       — thời hạn                                                               │
        │ Open Questions — vấn đề chưa chốt                                                       │
        │ Source         — transcript / timestamp                                                  │
        └─────────────────────────────────────────────────────────────────────────────────────────┘


AFTER SIGN-OFF
save approved note → keep transcript reference → use for follow-up / search / team memory
```

---

# AI tham gia ở đâu?

| Step | Thành phần | AI tham gia? | AI có quyết định? | Output |
|---|---|:---:|:---:|---|
| 1. Start Meeting | Discord / User | Không | Không | Bắt đầu phiên họp |
| 2. Audio / Transcript | System | Không | Không | Input cuộc họp |
| 3. Speech-to-Text | AI | Có | Không | Transcript |
| 4. Meeting Understanding | AI | Có | Có | Candidate summary / decision / action |
| 5. Enough Evidence? | AI | Có | **Có — quyết định chính** | Extract hoặc Need Confirmation |
| 6. Draft Meeting Note | AI | Có | Không | Biên bản nháp |
| 7. Human Review | User | Không | **Human quyết định cuối** | Confirm / Edit / Reject |
| 8. Publish Discord | System | Không | Không | Biên bản chính thức |

---

# Quyết định AI quan trọng nhất

```text
                           < AI DECISION >

            Thông tin này có đủ căn cứ trong transcript không?

                       /                     \
                     YES                      NO
                      │                        │
                      ▼                        ▼
             extract chính xác       "chưa xác định"
             + source/timestamp       + need confirmation
```

### Ví dụ 1 — đủ căn cứ

```text
Transcript:
"Khoa làm API nhé. Tối mai trước 9 giờ gửi bản chạy được."

AI:
Owner    = Khoa
Action   = Làm API
Deadline = trước 21:00 ngày mai
Status   = CONFIDENT
```

### Ví dụ 2 — chưa đủ căn cứ

```text
Transcript:
"Chắc Khoa làm API cũng được."

AI:
Possible Owner = Khoa
Action         = API
Deadline       = chưa xác định
Status         = NEED CONFIRMATION
```

---

# Boundary của AI

## AI được phép
- Chuyển audio thành transcript.
- Tóm tắt nội dung chính.
- Nhận diện candidate decision / action item / owner / deadline.
- Kiểm tra mức độ có căn cứ từ transcript.
- Sinh draft meeting note.
- Đánh dấu phần chưa chắc chắn.

## AI không được phép
- Tự tạo deadline khi người họp chưa nói.
- Tự gán owner khi chưa được giao rõ.
- Biến một đề xuất thành quyết định đã chốt.
- Khẳng định thông tin khi audio/transcript không rõ.
- Publish thông tin chưa xác nhận như một fact chắc chắn.

---

# Scope MVP cho CP2

```text
IN SCOPE
✓ /meeting start hoặc upload audio/transcript
✓ Speech-to-Text
✓ Extract Summary / Decisions / Action Items / Owner / Deadline
✓ AI decision: Enough Evidence?
✓ Need Confirmation
✓ Human Confirm / Edit / Reject
✓ Post kết quả lên Discord

OUT OF SCOPE
× tự giao task cho thành viên
× tự đổi deadline
× tự gửi lịch / reminder
× emotion analysis
× full meeting platform
× tự động thực thi action item
```

---

# Một câu mô tả flow

> **Học viên bật Meeting Mode hoặc cung cấp recording/transcript → AI hiểu cuộc họp và trích xuất các thông tin hành động → AI quyết định thông tin nào đủ căn cứ và thông tin nào cần xác nhận → người dùng duyệt → Trợ lý Kute đăng biên bản đã xác nhận lên Discord.**

---

# Điểm cần nhấn mạnh khi trình bày CP2

1. **AI không nằm ở mọi bước** — Discord/system xử lý capture, format và publish.
2. **AI decision rõ nhất là `Enough Evidence?`**.
3. **Human vẫn có quyền quyết định cuối** đối với thông tin không chắc chắn.
4. Flow phù hợp với mức automation **Conditional**.
5. Có đường xử lý failure thay vì ép AI luôn phải đưa ra câu trả lời.
