# Phản hồi trải nghiệm Bot Skynet Meeting Note

## Nguồn và phạm vi

- Nguồn: Google Form phản hồi trải nghiệm sản phẩm, xuất CSV ngày 18/09/2026.
- Số phản hồi: **5**.
- Báo cáo dùng mã Người thử 1–5 để không đưa tên hoặc mã sinh viên vào repository public.

## Kết quả tổng hợp

| Hạng mục | Kết quả |
|---|---|
| Slash commands (`/record`, `/note`, `/end-record`) | 4/5 (80%) đánh giá dễ dùng hoặc phản hồi nhanh; 1/5 (20%) chưa rõ bot đã bắt đầu ghi âm chưa. |
| Ghi chú cá nhân (`/note`) | 5/5 phản hồi tích cực: 4/5 thấy tiện khi đang họp, 1/5 nhấn mạnh ghi chú chỉ mình người dùng xem được. |
| Trích xuất Action Item | 4/5 (80%) đánh giá rất chính xác về task, owner và deadline; 1/5 (20%) đánh giá ở mức bình thường. |
| Evidence cho Action Item | 4/5 (80%) thấy evidence rất hữu ích để đối chiếu; 1/5 (20%) cho biết trích dẫn chưa khớp lời nói trong cuộc họp. |
| Lỗi khi trải nghiệm | 3/5 (60%) gặp một lỗi: bot vào voice nhưng không thu tiếng; không trả transcript sau `/end-record`; hoặc chuyển tab bị giật/lỗi. |

## Strengths

1. **Giá trị cốt lõi đã rõ.** Phần lớn người thử đánh giá Action Item chính xác, nhất là owner và deadline. Đây là tín hiệu tốt cho luồng tóm tắt sau họp.
2. **Evidence tạo được niềm tin.** Bốn người thấy bằng chứng hữu ích vì có thể đối chiếu lại nội dung. Đây là điểm khác biệt đáng giữ khi demo.
3. **`/note` có ích và riêng tư.** Người dùng thấy thao tác ghi chú tiện trong lúc họp; phản hồi cũng xác nhận kỳ vọng về quyền riêng tư của ghi chú cá nhân.
4. **Luồng lệnh cơ bản dễ tiếp cận.** Bốn người đánh giá slash command dễ dùng hoặc bot phản hồi nhanh.

## Weaknesses và ưu tiên cải thiện

| Ưu tiên | Weakness quan sát được | Bằng chứng | Hướng cải thiện |
|---|---|---|---|
| P0 | Recording không ổn định | 1 người báo bot đã vào voice nhưng không thu tiếng. | Khi `/record` bắt đầu, hiển thị trạng thái rõ ràng “đang ghi”; sau vài giây hiển thị số speaker hoặc mức audio đã nhận. Nếu chưa nhận audio, báo lỗi ngay thay vì chờ đến cuối cuộc họp. |
| P0 | Không có transcript sau `/end-record` | 1 người không nhận được bảng chép lời sau khi kết thúc. | Hiển thị tiến trình sau `/end-record`: “đang xử lý audio” → “đang tạo transcript” → “đang tạo biên bản”; khi lỗi phải có thông báo và cách thử lại. |
| P1 | Evidence chưa luôn đúng với lời nói | 1 người nói trích dẫn khó hiểu hoặc không khớp cuộc họp, dù Action Item được đánh giá đúng. | Mỗi Action Item cần giữ quote ngắn nguyên văn từ transcript; nếu transcript nhiễu hoặc mơ hồ, đưa vào `Needs Confirmation` thay vì dùng evidence yếu. |
| P1 | Trạng thái bắt đầu ghi chưa rõ | 1 người không biết bot đã thực sự bắt đầu thu hay chưa. | Thêm xác nhận rõ trong Discord và một chỉ báo recording đang hoạt động, ví dụ thời lượng ghi hoặc số người đang được thu. |
| P2 | Chuyển tab bị giật/lỗi | 1 người gặp lỗi ở tab Tóm tắt/Ghi chú/Bản chép lời. | Kiểm thử chuyển tab liên tiếp và khi transcript dài; thêm loading state hoặc tránh render toàn bộ transcript trong một embed quá lớn. |

## Kết luận

Bot đã chứng minh được lợi ích chính: Action Item, evidence và ghi chú cá nhân được người dùng đánh giá tích cực. Rủi ro lớn nhất hiện tại không nằm ở ý tưởng sản phẩm mà ở **độ tin cậy của pipeline recording → transcript → hiển thị kết quả**. Trước demo, nên ưu tiên xử lý lỗi thu âm và trạng thái xử lý sau `/end-record`; sau đó mới tối ưu trải nghiệm tab và độ chính xác evidence.

## Dữ liệu phản hồi đã ẩn danh

| Người thử | Slash commands | `/note` | Action Item | Evidence | Lỗi / góp ý |
|---|---|---|---|---|---|
| 1 | Chưa rõ bot đã bắt đầu thu hay chưa | Tiện khi đang họp | Rất chính xác | Rất hữu ích | Không gặp lỗi |
| 2 | Dễ dùng, phản hồi nhanh | Riêng tư, chỉ người dùng xem note | Rất chính xác | Chưa khớp lời nói | Evidence cần chính xác hơn |
| 3 | Dễ dùng, phản hồi nhanh | Tiện khi đang họp | Rất chính xác | Rất hữu ích | Bot vào voice nhưng không thu tiếng |
| 4 | Dễ dùng, phản hồi nhanh | Tiện khi đang họp | Rất chính xác | Rất hữu ích | Không có transcript sau `/end-record` |
| 5 | Dễ dùng, phản hồi nhanh | Tiện khi đang họp | Bình thường | Rất hữu ích | Chuyển tab bị giật/lỗi |
