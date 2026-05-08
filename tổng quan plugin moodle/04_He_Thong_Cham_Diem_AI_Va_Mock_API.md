# Cơ Chế Chấm Điểm (AI & AST) và Mock API

## 1. Hệ thống Khuyến nghị Bài tập (Mock API & Supabase)
Để gợi ý bài tập chuẩn xác, Moodle giao tiếp với `api_server.php` (chạy qua XAMPP port 8080).
- **Thu thập dữ liệu:** Khi sinh viên bấm xem gợi ý, Moodle gửi MSSV (vd `124001146`) và Mã khóa học.
- **Tính toán năng lực:** Mock API gọi cURL qua Supabase Cloud (CSDL phân tích học tập) để kéo cột `score` tương ứng với sinh viên đó trong môn học (vd: môn KTLT).
- **Thuật toán ánh xạ (Mapping Algorithm):**
  - Điểm < 5.0 -> Trình độ 1 (Dễ).
  - 5.0 <= Điểm <= 7.0 -> Trình độ 2 (Trung bình).
  - 7.0 < Điểm <= 9.0 -> Trình độ 3 (Khó).
  - Điểm > 9.0 -> Trình độ 4 (Chuyên gia).
- **Truy vấn Đề bài:** Mock API kết nối CSDL SQL Server (PersonalizedSystem) qua ODBC, sử dụng `CAST(col AS VARBINARY(MAX))` và hàm `iconv` để tự động xử lý lỗi Encoding tiếng Việt (UCS-2LE sang UTF-8). Sau đó bốc ngẫu nhiên (`ORDER BY NEWID()`) 5 bài đúng trình độ. Nếu thiếu bài, nó có cơ chế tự động hạ cấp (hạ chuẩn) để đảm bảo luôn đủ 5 bài cho người dùng.
- **Xử lý Regex UUID:** Mock API dùng biểu thức chính quy (Regex) `[A-Za-z0-9_-]+` thay cho `\w+` để chấp nhận tra cứu kết quả từ các ID có gạch ngang (như UUID từ hệ thống AI gửi sang).

## 2. Lõi chấm điểm thông minh: DSA Fusion (Local Server)
Mã nguồn của sinh viên (Python, C++...) được gửi nguyên gốc từ Moodle MUC sang **DSA Fusion Server** (FastAPI - port 8000).

### Thuật toán chấm bằng Trí Tuệ Nhân Tạo (Cloud LLM)
- Mặc định, Fusion gửi mã code lên máy chủ của Google (thông qua API Key cấu hình trong `.env`).
- Mô hình được chọn hiện tại là `gemini-2.0-flash`.
- AI không chỉ chấm đúng sai mà còn kiểm tra các yếu tố: Clean Code, Độ phức tạp thời gian $O(N)$, không gian bộ nhớ, và đưa ra lời nhận xét có tính con người nhất.

### Cơ Chế Dự Phòng (AST Fallback - Resilience)
Rủi ro khi xài AI Cloud là thỉnh thoảng Google chặn yêu cầu (Error 429: Quota Exceeded) hoặc lỗi mô hình (Error 404: Model Not Found). Thay vì báo lỗi sập trang, Fusion có bộ bắt ngoại lệ (Exception Handling) tự động **chuyển hướng sang chấm bằng AST (Abstract Syntax Tree)**.

#### Thuật toán AST hoạt động ra sao?
- Code của sinh viên được phân giải cú pháp thành cây cấu trúc AST.
- Hệ thống duyệt qua từng Node (hàm, vòng lặp, điều kiện) để kiểm tra logic. 
- AST kết hợp với bộ Unit Tests cục bộ để chạy code, nạp Input và so khớp Output.
- Mặc dù không có những nhận xét văn vẻ như con AI, AST đảm bảo **tính chính xác 100% và phản hồi với độ trễ (Latency) gần như bằng 0** ngay cả khi không có mạng Internet.
- Phía Moodle (Plugin) cũng góp phần che đậy cơ chế này bằng cách tự động dịch các cảnh báo kỹ thuật (Technical Logs) thành chữ nghĩa tiếng Việt: *"Hệ thống đã chấm điểm bằng thuật toán (không có nhận xét chi tiết cho test case này)"*, đảm bảo trải nghiệm sinh viên luôn hoàn hảo!
