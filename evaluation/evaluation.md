# Evaluation — Tiêu chí đánh giá bot Discord (Skynet)

Tiêu chí kiểm thử/đánh giá áp dụng sau khi bot Discord hoàn thiện (recording, commands, các quyết định AI trung tâm). Bám theo khối R4 · Kiểm thử của `04-rubric.md` và §7 của `spec.md`, cụ thể hoá cho bot hiện có.

## 1. Chiều chất lượng cần kiểm chứng

| Chiều | Định nghĩa kiểm chứng được | Cách đo |
|---|---|---|
| Đúng chức năng (Functional correctness) | Lệnh/slash command trả đúng kết quả mong đợi với input hợp lệ | So khớp output thực tế với expected output trong golden set |
| Độ tin cậy khi ghi âm (Recording reliability) | Bot join voice channel, ghi đủ audio từ lúc `/record start` đến `/record stop`, không mất đoạn | Nghe lại file audio, đối chiếu thời lượng thực tế vs. thời lượng phiên |
| Xử lý lỗi & edge case | Bot không crash khi gặp input sai, quyền thiếu, hoặc trạng thái bất thường (vd: stop khi chưa start) | Chạy các case lỗi trong golden set, xác nhận bot phản hồi rõ ràng thay vì im lặng/crash |
| Độ trễ phản hồi (Latency) | Thời gian từ khi gọi lệnh đến khi bot phản hồi nằm trong ngưỡng chấp nhận được | Đo thời gian thực tế, so với quality bar đã chốt |
| An toàn & phân quyền (Moderation/permissions) | Lệnh nhạy cảm (mute/kick/ghi âm) chỉ chạy đúng theo quyền, không bị lạm dụng | Test với tài khoản không đủ quyền, xác nhận bị từ chối đúng cách |
| Trải nghiệm hội thoại (nếu có quyết định AI) | Phản hồi của AI bám đúng context, không bịa (hallucination), báo rõ khi không chắc | Đối chiếu output AI với transcript/log gốc, đánh dấu case sai lệch |

## 2. Golden set (≥20 case, theo cơ cấu chuẩn)

- ≥2 case cho mỗi lớp "chỗ khó" (theo taxonomy ①②③④ trong spec — vd: input mơ hồ, thiếu quyền, bot bị gọi sai trạng thái, dữ liệu ngoài phạm vi).
- 8–10 case thường (happy path: start/stop recording, các slash command cơ bản).
- 2–4 case hiếm (mất kết nối voice giữa chừng, nhiều user cùng lúc gọi lệnh, bot bị kick khỏi channel khi đang ghi).
- ≥10 case lấy từ chatlog/log thực tế của bot (không tự bịa toàn bộ).
- Lưu toàn bộ case trong thư mục `evaluation/` (input, expected output, kết quả thực tế).

## 3. Quality bar

- Chốt bằng con số cụ thể trước hạn, giữ nguyên sau đó, ví dụ dạng: "Đạt khi ≥ 80% case pass, và 100% case liên quan an toàn/phân quyền phải pass."
- Ghi rõ điều kiện pass/fail cho từng chiều chất lượng ở mục 1.

## 4. Bảng kết quả chạy

| Lượt chạy | Ngày | Tổng case | Pass | Fail | % Pass | Ghi chú (nguyên nhân case fail) |
|---|---|---|---|---|---|---|
| Lượt 1 (Audio Golden Set) | 18/09/2026 | 10 | 9 | 1 | 90.0% | TC06: Expected 0 action items for feedback/review meeting, got 1 |
| Lượt 2 | | | | | | |

- Ghi nhận đầy đủ, trung thực mọi case kể cả case chưa đạt — không chỉnh sửa/che giấu số liệu.
- Với case fail: phân tích nguyên nhân (bug code, giới hạn model AI, thiếu quyền Discord API, v.v.) và hướng khắc phục.

## 5. Kiểm thử thủ công bổ sung (trước demo)

- [ ] Bot online ổn định, không lỗi khi `setup_hook` load extension.
- [ ] Slash command sync đúng vào guild test.
- [ ] Ghi âm test với ≥2 người nói cùng lúc trong voice channel.
- [ ] Dừng ghi âm đột ngột (bot bị kick, mất mạng) không làm crash tiến trình chính.
- [ ] File audio/transcript xuất ra đúng định dạng, nghe/đọc được.
