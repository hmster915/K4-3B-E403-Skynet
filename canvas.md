# Canvas CP1 — Nhóm Skynet · Lớp 3B

> Scaffold 7 dòng theo `02-guide.md` §1.5 · mẫu: `examples/canvas-cp1.md`
> Đội trưởng nộp form: **[Họ tên]** · MSSV **[điền]** · Repo: https://github.com/hmster915/K4-3B-E403-Skynet

---

**1. Track + đề:** B · Trợ lý Discord — **tính năng mới**: biên bản họp tự động cho nhóm build (họp nhóm & họp với mentor trong kênh voice Discord).

**2. Job executor:** Thành viên nhóm hackathon vừa họp xong trong kênh voice Discord — hoặc người vắng buổi họp đó — đang cần biết nhóm đã chốt gì và việc của mình là gì.

**3. Pain:** Kết quả buổi họp chỉ nằm trong trí nhớ người có mặt; người vắng phải hỏi lại từ đầu, và đến hạn `/daily-standup` sáng hôm sau không ai nhớ chính xác "hôm qua làm gì / hôm nay làm gì / blocker" — việc bị trôi và standup nộp trễ hoặc chung chung.

**4. Bằng chứng đầu:**

*Bằng chứng trực tiếp — ĐANG THU, là nguồn chính (chuẩn A, chốt trước hạn chốt spec 21:00 18/9):*
- Khảo sát ≥20 học viên ngoài nhóm, hỏi về **lần gần nhất** chứ không hỏi ý kiến: *"Lần gần nhất nhóm bạn họp xong, bạn ghi lại kết quả bằng gì? Người vắng hôm đó biết việc của mình kiểu nào?"* — log đầy đủ (câu hỏi · từng câu trả lời nguyên văn · ai trả lời) trong `evidence/`.
- Bar nhóm đặt: ≥50% xác nhận có gặp vấn đề + ≥5 quote nguyên văn. Kết quả tính đến CP1: `[n = __ , __/__ xác nhận]`

*Bối cảnh mining — đếm được nhưng CHỈ chứng minh bối cảnh, không chứng minh pain:*
- `66/779` tin của người (**8,5%**, từ **34** người khác nhau) nhắc `daily-standup` trong 3 ngày 12–14/09. *Cách đếm:* lọc `is_bot = False` trong `data/discord-pack/k4_messages.csv`, regex `stand[\s-]?up` trên cột `content`. **Đọc kỹ 66 tin: phần lớn hỏi thủ tục (nộp ở đâu, cú pháp, mấy giờ được XP), không phải "không biết viết gì".** Nó chỉ nói: nghĩa vụ báo cáo hằng ngày có thật và đang tốn sự chú ý của lớp.
- `M99277` — "Tạo kênh voice riêng cho nhóm kiểu gì" · `M61254` — "Mình lỡ mất buổi workshop và dailystandup hôm qua thì có ảnh hưởng như thế nào". Hai tin, đúng hai tin: có nhóm họp bằng voice, và vắng mặt là chuyện thật. **Chưa phải bằng chứng pain.**

> **Vì sao mining không đủ ở đây:** data pack chỉ có tin nhắn text, buổi họp của nhóm diễn ra trong kênh voice — pack không với tới được. Nên bằng chứng phải đến từ khảo sát người thật, mining chỉ đóng vai bối cảnh.

**5. Lát cắt MỘT CÂU:** Một thành viên vừa họp xong · cần biên bản để nộp standup · AI quyết định câu nào trong transcript là **quyết định đã chốt / việc đã có người nhận** và câu nào chỉ là bàn tán · xuất bản nháp 3 mục (chốt gì · ai làm gì trước khi nào · điểm chưa ngã ngũ), mỗi dòng trỏ về timestamp nguồn.

**6. AI tự làm đến đâu — `conditional`:**
*Tự:* nhận bản ghi âm buổi họp → transcript → phân loại từng đoạn → sinh bản nháp biên bản có trích timestamp.
*Không tự:* **không tự đăng lên kênh** — bản nháp phải có một người trong nhóm duyệt; dòng nào không trỏ được về một đoạn transcript cụ thể thì **không được ghi "đã chốt"**, phải xếp xuống mục "chưa rõ".
*Lý do:* gán sai việc cho người hoặc ghi sai deadline gây hậu quả thật; và ghi âm người khác phải báo trước + có đồng ý — bot thông báo "đang ghi âm" khi vào kênh voice và bất kỳ ai cũng dừng được.
**Willing users (ngoài nhóm, đã hỏi và đồng ý):** `[Tên 1]` · `[Tên 2]` · `[Tên 3]`

**7. Phân công:**
| Việc | Người |
|---|---|
| Evidence: mining + khảo sát, log đầy đủ | `[Tên]` |
| Spec + canvas + golden set | `[Tên]` |
| Bot Discord: vào voice, ghi âm, transcript | `[Tên]` |
| Prompt + lời gọi AI thật, phân loại chốt/bàn tán | `[Tên]` |
| UI duyệt + demo, user test, changelog | `[Tên]` |

---

### TA tích ở CP1 *(`04-rubric.md`)*
- ☐ Lát cắt đúng format 1 câu → dòng 5
- ☐ Có evidence ban đầu → dòng 4
- ☐ Đủ tên phân công → dòng 7 *(còn trống — điền trước 19:30)*

### Còn phải điền trước khi nộp
1. **Khảo sát 10–15 bạn trong lớp** (10 phút giờ nghỉ) → điền `n` và số xác nhận vào dòng 4, log nguyên văn vào `evidence/`
2. Tên + MSSV đội trưởng (cả 5 mốc phải cùng một mã học viên)
3. Tên trong bảng phân công (dòng 7)
4. ≥3 willing users đã hỏi và đồng ý (dòng 6) — CP5 khối R6 yêu cầu ≥2 người đã khai ở mốc này
5. Repo để **Public** trong Settings
