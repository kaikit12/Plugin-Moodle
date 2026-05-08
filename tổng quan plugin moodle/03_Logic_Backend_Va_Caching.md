# Logic Xử Lý Backend PHP & Cơ Chế Caching

## 1. Cấu trúc và Vị trí
Mã nguồn Backend của plugin nằm trong thư mục `D:\Code\Moodle\local_exercise_suggestion\`.
Bao gồm các lớp (Layers) rõ ràng:
- **Controller:** `index.php` (Giao diện web) và `ajax.php` (API Endpoint nội bộ).
- **Service:** `classes/services/exercise_service.php` (Business Logic & Caching).
- **API Client:** `classes/api/client.php` và `classes/api/response_handler.php` (Giao tiếp External HTTP).

## 2. API Endpoint (`ajax.php`)
Đây là cửa ngõ duy nhất (Gateway) giữa Moodle Frontend và Backend nội bộ.
- **Bảo mật:** Sử dụng `require_login()` để chặn truy cập vãng lai. Kiểm tra `sesskey` để ngăn chặn tấn công CSRF (Cross-Site Request Forgery).
- **Xử lý ID:** Tách biệt 2 loại ID:
  - `$moodle_userid = $USER->id`: (Dạng số nguyên `2`, `5`...) dùng cho các hàm nội bộ của Moodle (vd: `enrol_get_users_courses`, ghi DB log `mdl_local_exsug_logs`).
  - `$username = $USER->username`: (Mã số sinh viên `124001146`) dùng để truyền ra ngoài Mock API và Fusion API nhận diện sinh viên.

## 3. Lớp Dịch Vụ - Business Logic (`exercise_service.php`)
Chịu trách nhiệm thực thi nghiệp vụ cốt lõi:
1. **Lọc dữ liệu rác (Sanitize):**
   - Ẩn dấu nhẹm các log lỗi kỹ thuật từ hệ thống AI Cloud. Cụ thể, khi AI trả về lỗi `[WARNING]`, `Error`, hàm `strpos` sẽ phát hiện và đổi nội dung hiển thị thành: *"Hệ thống đã chấm điểm bằng thuật toán (không có nhận xét chi tiết cho test case này)."* để tránh gây bối rối cho sinh viên.
2. **Quản lý Cache (Moodle MUC - Cache API):**
   - Sử dụng định nghĩa cache riêng: `cache::make('local_exercise_suggestion', 'apiresponses')`.
   - **Xử lý Key Cache:** Key của Moodle yêu cầu phải là "Simple keys" (chỉ gồm `a-z`, `0-9`, và `_`). Vì DSA Fusion sinh ra `submission_id` dạng UUID (chứa dấu gạch ngang `-`), hệ thống phải dùng hàm `str_replace('-', '_', $submissionid)` để đổi toàn bộ thành gạch dưới trước khi lưu vào Cache. Tránh làm sập bộ nhớ Moodle.

## 4. Quản lý Vòng đời Dữ liệu (TTL - Time To Live)
Để tối ưu hóa, hệ thống không gọi API liên tục mà ghi đè qua Cache:
- **Bài tập gợi ý (Suggestions):** Lưu Cache 3600 giây (1 giờ). Key dạng: `sug_{userid}_{courseid}`.
- **Chi tiết bài tập (Exercise):** Lưu Cache 3600 giây. Key dạng: `ex_{exerciseid}`.
- **Kết quả nộp bài (Result):** Lưu Cache 300 giây (5 phút). Khi sinh viên vừa submit, Backend không cần chờ mà tự động "ơm" (set) kết quả thật vào Cache (với Key `res_{uuid_đã_fix}`). Nếu sinh viên mở lại trang kết quả trong vòng 5 phút, Moodle sẽ load thẳng từ RAM ra, tốc độ tính bằng mili-giây, không tốn bất kỳ một request HTTP nào.

## 5. Ghi Log vào Database (Analytics)
Hàm `log_api_call` sẽ ghi nhận mọi hành động (Lấy gợi ý, Xem bài, Nộp bài) vào bảng `mdl_local_exsug_logs` trong CSDL của Moodle. Dữ liệu này cực kỳ hữu ích cho Giảng viên xem báo cáo sau này. Lỗi "Incorrect integer value" trước đây đã được fix bằng cách luôn ép `$USER->id` cho cột `userid`.
