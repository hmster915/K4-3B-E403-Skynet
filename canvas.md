# Canvas CP1 — Nhóm Skynet · Lớp 3B

> Scaffold 7 dòng theo `02-guide.md` §1.5 · mẫu: `examples/canvas-cp1.md`
> Đội trưởng nộp form: **[Họ tên]** · MSSV **[điền]** · Repo: https://github.com/hmster915/K4-3B-E403-Skynet

---

**1. Track + đề:** B · Trợ lý Discord — **tính năng mới**:  Meeting Mode + AI Meeting Summary cho các buổi mentor, workshop, team call và các cuộc họp thực tế có điều kiện thu âm phù hợp..

**2. Job executor:** Học viên vừa kết thúc một buổi mentor/workshop/team meeting, đang cần biết chính xác team phải làm gì tiếp theo sau cuộc họp.

**3. Pain:** Sau cuộc họp, nội dung thường nằm rải rác trong trí nhớ, chat, transcript hoặc ghi chú thủ công; học viên phải tự tìm lại **quyết định, việc cần làm, người phụ trách và deadline**, nên dễ bỏ sót, nhớ sai hoặc phải hỏi lại người khác.

**4. Bằng chứng đầu:**

File Evidence  : evidence.md
File Result  : result.md

**5. Lát cắt MỘT CÂU:** Học viên tham gia một buổi mentor/team meeting · bật Meeting Mode khi môi trường thu âm phù hợp · AI phân tích audio/transcript để quyết định đâu là decision, action item, owner và deadline có căn cứ · sau buổi họp trả về một biên bản ngắn có cấu trúc ngay trên Discord.
**6. AI tự làm đến đâu — `conditional`:**
*Tự:* 
- Nhận audio hoặc transcript của cuộc họp.
- Chuyển audio thành transcript nếu cần.
- Tóm tắt nội dung chính.
- Trích xuất:
  - Decisions
  - Action Items
  - Owner
  - Deadline
  - Open Questions
- Chỉ điền thông tin khi có căn cứ trong cuộc họp.
- Trả biên bản về Discord sau khi cuộc họp kết thúc.
*Không tự:*
 - Không tự suy đoán owner khi cuộc họp không nói rõ.
- Không tự đặt deadline.
- Không tự tạo decision nếu người tham gia chưa chốt.
- Không khẳng định nội dung khi transcript/audio không rõ.
- Nếu thiếu căn cứ, ghi **“chưa xác định”** hoặc đánh dấu cần người dùng xác nhận.
*Lý do:* Tóm tắt sai action item, owner hoặc deadline có thể khiến team thực hiện sai việc. Audio thực tế cũng có thể nhiễu hoặc thiếu người nói, nên AI phải thể hiện rõ mức độ chắc chắn thay vì tự điền.

**7. Phân công:**
- `Nguyen Khanh Linh_02409` — evidence + khảo sát + dataset meeting/transcript
- `Phung Trong Chien_02430` — prompt/extraction + output schema + Discord bot + tool schema
- `Nguyen Hong Khoa_02534` — Discord bot + Meeting Mode + backend/API 
- `Ngo Le Thuy Tien-02614` — eval + spec + demo + user test 

---
