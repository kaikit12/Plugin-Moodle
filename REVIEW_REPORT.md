# Plugin Code Review: `local_exercise_suggestion`

Sau khi kiểm tra mã nguồn hiện tại của plugin `local_exercise_suggestion` trong thư mục của bạn, tôi nhận thấy có **sự khác biệt khá lớn** giữa code hiện tại và **Kiến trúc 2-Phase (Push & Pull)** mà chúng ta vừa chốt ở `DATA_PIPELINE.md`.

Dưới đây là các điểm cần khắc phục để đáp ứng đúng yêu cầu:

---

## 1. Thiếu tính năng Đồng bộ dữ liệu (Phase 1 - Push Data)
- **Tình trạng:** Trong code hiện tại (`exercise_service.php`, `client.php`), KHÔNG CÓ đoạn mã nào thực hiện việc Extract điểm số (grades), nhật ký hoạt động (logs) từ `Global $DB` của Moodle.
- **Vấn đề:** Hệ thống Core AI không có data lịch sử của sinh viên để phân tích.
- **Giải pháp:** Cần bổ sung logic (như trong hàm `extract_moodle_data` ở `DATA_PIPELINE.md`) và thêm một cơ chế Moodle Scheduled Task (Cron job) `classes/task/sync_student_data_task.php` để chạy ngầm việc đẩy dữ liệu lên AI Core mỗi đêm.

## 2. Luồng Lấy Gợi Ý (Phase 2 - Pull Data) đang dùng API thay vì DB
- **Tình trạng:** File `classes/api/client.php` đang dùng cURL gọi tới endpoint `/api/suggestions` để lấy khuyến nghị bài tập về.
- **Đánh giá:** 
  - Nếu đối tác thứ 3 **có cung cấp API** `/api/suggestions` để Moodle lấy kết quả bài tập đã tính sẵn -> **Code hiện tại của bạn ĐANG LÀM RẤT TỐT**, bạn có đầy đủ Retry logic, timeout, và cả Caching.
  - Tuy nhiên, nếu đối tác yêu cầu Moodle truy cập **thẳng vào Database (MySQL/PostgreSQL) của họ** theo thiết kế trước đó -> Thì file `client.php` chưa đáp ứng được, bạn sẽ phải viết class dùng `\PDO` để query trực tiếp như tôi đã hướng dẫn.

## 3. Cấu hình (`settings.php`) chưa đồng bộ
- **Tình trạng:** Khai báo cấu hình mới chỉ dừng ở mức nhận `api_url` và `api_key`.
- **Giải pháp:** Nếu dùng API, bạn nên cấu hình 2 đường link độc lập:
  - `push_api_endpoint`: Nơi đẩy data quá khứ lên.
  - `pull_api_endpoint`: Nơi lấy list gợi ý về.
  - Nếu dùng DB ngoài, bạn cần thêm form input cho `db_host`, `db_user`, `db_pass`.

## ⏭️ Đề xuất Hướng Đi Tiếp Theo
Code khung API hiện tại của bạn viết rất chuẩn (chuẩn OOP của Moodle, có cache system bài bản). Do đó:
1. Bạn nên hỏi lại bên Thứ 3: *"Họ sẽ trả kết quả bài tập gợi ý qua một API endpoint cho mình gọi vào, hay họ bắt mình query thẳng vào Database của họ?"* (Nếu trả qua API thì giữ nguyên bộ core `api/client.php` hiện tại).
2. Viết thêm Scheduled Task chạy Cron để nhồi data Moodle vào hệ thống của họ để họ có cơ sở phân tích trình độ Sinh viên.
