# PROJECT CONTEXT: `local_exercise_suggestion`

## 1. System Overview
Plugin `local_exercise_suggestion` là một **API Consumer (Moodle Local Plugin)**.  
Nhiệm vụ cốt lõi: Kết nối với một hệ thống AI Third-party thông qua REST API (được bảo mật bằng API Key), fetch danh sách "Bài tập đề xuất" được cá nhân hóa theo `user_id` và hiển thị trực tiếp lên giao diện Moodle của sinh viên một cách mượt mà nhất có thể (mô hình Pull Data Real-time có Caching). Plugin KHÔNG tự tính toán logic AI hay quản lý điểm số phức tạp.

---

## 2. File Structure & Current Status

Dưới đây là mapping các thành phần hiện tại trong source code:

| File / Folder | Chức năng Cốt lõi | Trạng thái |
| :--- | :--- | :--- |
| `classes/api/client.php` | API Wrapper dùng cURL (POST/GET) gọi dữ liệu từ hệ thống ngoài, xử lý Timeout & Retry. | ✅ Đã hoàn thiện |
| `classes/api/response_handler.php`| Validate tính hợp lệ của JSON Schema trả về từ API. | ✅ Đã hoàn thiện |
| `classes/services/exercise_service.php`| Tầng Business Logic: Wrap API client, xử lý Moodle Caching (tránh spam API ngoài). | ✅ Đã hoàn thiện |
| `classes/models/progress_tracker.php`| Quản lý tiến độ làm bài tạm thời trên Moodle. | ⚠️ Đang Disabled (Sai DB Schema) |
| `classes/models/logger.php` | Ghi log thống kê các request API thành công/thất bại vào bảng DB. | ✅ Đã khởi tạo |
| `classes/output/main_renderer.php` | Fallback basic renderer HTML (ít được dùng). | ✅ Đã tồn tại |
| `templates/*.mustache` | Giao diện hiển thị danh sách bài (suggestions_list), chi tiết (exercise_view), kết quả (result_view). | ✅ Đã hoàn thiện UI/UX |
| `index.php` | Controller File, Route các action (`list`, `view`, `submit`, `result`), gọi Service -> truyền data cho Mustache render. | ✅ Đã hoàn thiện |
| `settings.php` | Khai báo UI cấu hình Plugin cho Admin (API URL, API Key, Cache TTL). | ✅ Đã hoàn thiện |
| `db/*` | Khai báo DB Tables (`install.xml`), Caches (`caches.php`), Permissions (`access.php`). | ✅ Đã hoàn thiện |

---

## 3. Data Flow Analysis (Luồng dữ liệu hiện tại)

Dựa trên cấu trúc file `index.php`, hệ thống hiện tại đang chạy theo luồng **Page Navigation (Chuyển trang PHP truyền thống)**:

1. **Trigger:** User truy cập URL `/local/exercise_suggestion/index.php?courseid=XXX&action=list`.
2. **Controller (`index.php`):** Khởi tạo `exercise_service` và gọi hàm `$service->get_suggestions($userid, $courseid)`.
3. **Service Layer (`exercise_service.php`):** 
   - Check Moodle Caches (TTL: 3600s). Nếu hit -> Trả luôn.
   - Nếu miss -> Gọi `client->get_suggestions`.
4. **API Client (`client.php`):** Build cURL POST request tới hệ thống AI. Trả về JSON list.
5. **View Rendering:** `index.php` mapping JSON thành mảng biến, gọi `OUTPUT->render_from_template('local_exercise_suggestion/suggestions_list', $data)`. Giao diện (thẻ Card, CSS đẹp mắt) được đẩy ra trình duyệt.

**Đánh giá:** Luồng data cốt lõi hoạt động bình thường, không đứt gãy. Cấu trúc chia Controller - Service - API Client cực kỳ chuẩn chỉ (Clean Architecture). 

---

## 4. Missing Components (Các thành phần còn thiếu để chạy thực tế)

Mô hình hiện tại đang chạy Page-load PHP (`index.php`). Tuy nhiên, để đáp ứng chuẩn User Journey "Bấm nút hiện popup ngay trên UI khóa học", plugin **đang thiếu những components cực kỳ quan trọng sau**:

1. **AJAX Endpoint (`ajax.php`):**
   - Hiện tại đang dùng `index.php` để chuyển trang. Cần 1 file `ajax.php` hứng request ngầm và trả về mã HTML hoặc JSON để update UI không cần load lại trang.

2. **Moodle AMD JavaScript Module (`amd/src/main.js`):**
   - Thiếu hoàn toàn tầng JS để bắt sự kiện click nút "Gợi ý", gọi AJAX request, hiển thị hiệu ứng Loading Spinner (Shimmer UI), và append mã HTML nhận được vào giao diện hiện tại qua Mustache JS rendering. 

3. **Cơ chế Hook/Injection UI vào Course (`lib.php` hoặc Block):**
   - Thiếu hàm hook nội bộ của Moodle để tự động chèn cái "Nút Bấm Gợi ý" vào trang hiển thị môn học (Course View). Phương án tốt nhất là tạo một Block `blocks/exercise_suggestion` kèm theo, hoặc dùng output renderers overriding trong `lib.php`.

4. **Ngôn ngữ (Lang Strings):**
   - Cần kiểm tra xem file `lang/en/local_exercise_suggestion.php` đã định nghĩa đủ key cho `pluginname`, `api_key`, `error:apierror` như bị báo throw Exception trong `index.php` hay chưa.
