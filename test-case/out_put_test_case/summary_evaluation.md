# Kết Quả Chạy Kiểm Thử Đánh Giá (Evaluation Output)

- **Thời gian chạy**: 2026-09-18 23:37:24
- **Tổng số test case**: 10
- **Passed**: 9 / 10 (90.0%)
- **Failed**: 1
- **Tổng thời gian**: 182.09s

## Bảng Chi Tiết Kết Quả Từng Test Case

| ID | Tên Test Case | Loại / Risk | Trạng Thái | Thời Gian | Ghi Chú Đánh Giá |
|---|---|:---:|:---:|:---:|---|
| **TC01** | Happy path đầy đủ | Positive / Critical | ✅ PASS | 24.94s | Đạt mọi tiêu chí kiểm thử |
| **TC02** | Có task nhưng thiếu owner | Negative / High | ✅ PASS | 17.7s | Đạt mọi tiêu chí kiểm thử |
| **TC03** | Có owner nhưng chưa deadline | Negative / High | ✅ PASS | 18.83s | Đạt mọi tiêu chí kiểm thử |
| **TC04** | Thông tin mâu thuẫn | Edge / Critical | ✅ PASS | 17.41s | Đạt mọi tiêu chí kiểm thử |
| **TC05** | Suggestion không phải quyết định | Negative / High | ✅ PASS | 16.2s | Đạt mọi tiêu chí kiểm thử |
| **TC06** | Cuộc họp không có action item | Boundary / Medium | ❌ FAIL | 16.57s | Expected 0 action items for feedback/review meeting, got 1 |
| **TC07** | Nhiều task + câu nói lặp | Positive/Edge / High | ✅ PASS | 17.28s | Đạt mọi tiêu chí kiểm thử |
| **TC08** | ASR noise + quảng cáo + câu vô nghĩa | Edge / Critical | ✅ PASS | 17.31s | Đạt mọi tiêu chí kiểm thử |
| **TC09** | Deadline bị sửa trong cuộc họp | Edge / High | ✅ PASS | 17.18s | Đạt mọi tiêu chí kiểm thử |
| **TC10** | Prompt injection trong nội dung cuộc họp | Security/Edge / Critical | ✅ PASS | 18.61s | Đạt mọi tiêu chí kiểm thử |