# Skynet Bot – Meeting Audio Test Cases

Mục tiêu: kiểm thử luồng **Audio → Speech-to-Text → Skynet extraction** cho các thông tin trong cuộc họp như **Decision, Task, Owner, Deadline, Priority, Dependency và Ambiguity**.

| # | Trường hợp | Audio / Câu nên nói | Bot cần hiểu |
|---|---|---|---|
| 1 | Task + Owner + Deadline rõ | “Linh hoàn thiện UI trước tối mai nhé.” | Task: hoàn thiện UI · Owner: Linh · Deadline: tối mai |
| 2 | Nhiều task liên tiếp | “Linh làm UI, Khoa hoàn thiện backend, Chiến chốt extraction schema, Tiến chuẩn bị eval.” | 4 task + 4 owner |
| 3 | Decision rõ | “Ok team mình chốt giữ Discord flow cho prototype nhé.” | Decision: giữ Discord flow |
| 4 | Task không có deadline | “Khoa lo phần backend nhé.” | Owner + task, deadline chưa xác định |
| 5 | Task không có owner | “Phần demo cần hoàn thiện trước thứ Sáu.” | Task + deadline, owner chưa xác định |
| 6 | Deadline tương đối | “Phần eval cố gắng xong trước buổi mentor tiếp theo.” | Giữ deadline dạng relative |
| 7 | Sửa deadline | “UI xong thứ Năm nhé… à thôi, chuyển sang thứ Sáu.” | Deadline cuối = thứ Sáu |
| 8 | Đổi owner | “Linh làm phần slide nhé… khoan, để Tiến làm slide đi.” | Owner cuối = Tiến |
| 9 | Huỷ task | “Chiến làm dashboard nhé… à dashboard chưa cần, bỏ phần đó.” | Không đưa dashboard vào task cuối |
| 10 | Một task nhiều owner | “Linh với Khoa cùng chuẩn bị demo cuối tuần này.” | Owner: Linh + Khoa |
| 11 | Một người nhiều task | “Linh hoàn thiện UI trước tối mai, rồi chuẩn bị script demo trước thứ Sáu.” | 2 task cùng Owner Linh |
| 12 | Task mơ hồ | “Phần này mọi người tự align với nhau nhé.” | Không tự bịa task/owner |
| 13 | Brainstorm chưa chốt | “Có thể mình dùng Discord, hoặc chuyển sang web app cũng được, để xem thêm đã.” | Chưa có decision |
| 14 | Chốt sau brainstorm | “Discord hay web đều được… thôi chốt Discord để kịp demo.” | Decision cuối = Discord |
| 15 | Có điều kiện | “Nếu API ổn trước thứ Năm thì Khoa tích hợp luôn vào demo.” | Task có condition: API ổn trước thứ Năm |
| 16 | Dependency giữa task | “Khoa xong backend trước, sau đó Linh mới nối UI vào API.” | Task order/dependency: backend → UI integration |
| 17 | Priority | “Ưu tiên cao nhất là Meeting Mode, dashboard để sau.” | Priority: Meeting Mode > Dashboard |
| 18 | Người nói tự nhận task | “Phần eval để em làm, em sẽ gửi kết quả tối mai.” | Owner = người đang nói · Task = eval · Deadline = tối mai |
| 19 | Transcript nhiều filler | “Ờ… Linh nhé, kiểu… em hoàn thiện cái UI ấy, cố gắng trước tối mai nha.” | Vẫn extract đúng task/owner/deadline |
| 20 | Thông tin xung đột cần hỏi lại | “Linh làm UI trước tối mai… mà Khoa cũng đang làm UI rồi thì phải.” | Nhận diện ambiguity/conflict, không tự chọn owner |

## Sample realistic meeting segment

> “Prototype mình giữ Discord flow nhé. Linh hoàn thiện UI trước tối mai. Khoa lo backend với Meeting Mode. Chiến chốt extraction schema. Tiến chuẩn bị eval. À phần eval thì không cần xong tối mai đâu, trước buổi mentor tiếp theo là được.”

### Expected extraction

- **Decision:** Giữ Discord flow.
- **Linh:** Hoàn thiện UI → tối mai.
- **Khoa:** Backend + Meeting Mode → chưa có deadline.
- **Chiến:** Chốt extraction schema → chưa có deadline.
- **Tiến:** Chuẩn bị eval → trước buổi mentor tiếp theo.

## Evaluation criteria

- **Accuracy:** đúng task, owner, deadline, decision.
- **Completeness:** không bỏ sót thông tin quan trọng.
- **No hallucination:** không tự điền thông tin chưa có.
- **Conflict handling:** nhận diện sửa lời, đổi owner, huỷ task, thông tin mâu thuẫn.
- **Traceability:** có thể truy lại transcript/source khi recall.
