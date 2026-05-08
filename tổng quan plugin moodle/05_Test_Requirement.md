# Test Requirement (Yêu cầu kiểm thử)

## 1. Mục đích và Phạm vi kiểm thử
Tài liệu này xác định các yêu cầu kiểm thử đối với Plugin `local_exercise_suggestion` (Hệ thống đề xuất và chấm bài tập bằng AI).
- **In-scope (Phạm vi kiểm thử):**
  - Giao diện người dùng (Frontend UI/UX) trên Moodle.
  - API nội bộ `ajax.php`.
  - Luồng giao tiếp với Mock API Server (Gợi ý bài tập).
  - Luồng giao tiếp với DSA Fusion Server (Chấm code bằng AI / AST).
  - Hệ thống Caching của Moodle.
- **Out-of-scope (Ngoài phạm vi):**
  - Hệ thống lõi của Moodle.
  - Lõi của nền tảng Supabase.

## 2. Môi trường kiểm thử (Test Environment)
- **Hệ điều hành:** Windows (Localhost)
- **Web Server:** XAMPP (Apache, PHP 8.x)
- **Database:** MySQL/MariaDB (Moodle DB), SQL Server (Mock API)
- **AI Server:** Python 3.10+, FastAPI (chạy tại cổng 8000)
- **Trình duyệt:** Google Chrome, Microsoft Edge (Phiên bản mới nhất)
- **Tài khoản test:** Tài khoản Sinh viên (vd: `124001146`), Tài khoản Admin.

## 3. Các yêu cầu chức năng cần kiểm thử (Test Requirements)

### TR_01: Kiểm thử Giao diện (UI/UX)
- Nút FAB phải xuất hiện đúng vị trí và không bị che khuất.
- Cửa sổ Modal phải bật lên mượt mà, hỗ trợ đóng/mở chuẩn xác.
- Khi đang nộp bài, nút "Submit" phải bị vô hiệu hóa (disabled) để chống spam.

### TR_02: Kiểm thử Luồng Đề xuất bài tập (Suggestion System)
- Gọi API thành công để kéo điểm năng lực từ Supabase.
- Hiển thị đúng 5 bài tập tương ứng với độ khó.
- Nếu CSDL thiếu bài tập ở độ khó nhất định, hệ thống phải tự động hạ chuẩn và lấy đủ 5 bài ngẫu nhiên.

### TR_03: Kiểm thử Chấm điểm Code (AI & AST)
- Gửi code và nhận về kết quả dạng JSON.
- Phân tích và chấm chính xác code đúng, code sai cú pháp, code tối ưu kém (vòng lặp thừa).
- Hiển thị điểm số, lời nhận xét, và kết quả từng testcase rõ ràng.

### TR_04: Kiểm thử Cơ chế Dự phòng (Resilience & Fallback)
- Xử lý tình huống API Key Google hết hạn ngạch (Error 429) hoặc sai Model (Error 404).
- Hệ thống không được "chết", phải tự động chuyển sang chấm bằng AST.
- Giao diện phải ẩn thông báo lỗi kỹ thuật và hiển thị thông điệp thân thiện với sinh viên.

### TR_05: Kiểm thử Hiệu năng và Caching
- Các API lấy đề xuất và lấy chi tiết bài tập phải được lưu Cache (3600 giây).
- Bài nộp sau khi chấm xong phải được lưu Cache ngay lập tức (300 giây).
- Refresh trang kết quả trong 5 phút đầu phải load từ Cache (0ms) thay vì gọi lại Mock API.

### TR_06: Kiểm thử Bảo mật (Security)
- File `ajax.php` phải từ chối mọi yêu cầu nếu người dùng chưa đăng nhập.
- Yêu cầu phải có `sesskey` hợp lệ.
