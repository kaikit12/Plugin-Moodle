# Tài liệu Kiến trúc Data Pipeline - Plugin `local_exercise_suggestion`

Plugin `local_exercise_suggestion` được thiết kế với mục tiêu cốt lõi: **Lấy dữ liệu bài tập đã được AI cá nhân hóa từ hệ thống bên thứ 3 (Third-party System) và hiển thị trực tiếp lên giao diện học tập của Moodle.** 

Tất cả các logic phức tạp về phân tích trình độ tay nghề, tính điểm hay lịch sử đều do Core AI bên kia đảm nhiệm. Plugin đóng vai trò là một **Consumer API** hoàn hảo.

---

## 1. Luồng Lấy Dữ Liệu (Pull Data Pipeline)

Quy trình diễn ra theo thời gian thực (Real-time) ngay khi người dùng yêu cầu:

1. **Trigger:** Sinh viên bấm nút "Gợi ý bài tập" trên giao diện Moodle.
2. **Service Layer (Xử lý & Cache):** Gọi vào `exercise_service->get_suggestions()`. Hệ thống sẽ check Moodle Cache (`$this->cache`) để xem đã có dữ liệu gần đây chưa (nhằm giảm tải).
3. **API Client Layer (Giao tiếp):** Nếu không có Cache, gọi tới `api\client.php`. Class này dùng cURL để POST dữ liệu căn bản (`user_id`, `course_id`) sang API `/api/suggestions` của hệ thống thứ 3. Đi kèm là các Header Authentication (`API Key`).
4. **Response & Render:** Core AI trả về cấu trúc JSON danh sách bài tập. Hệ thống lưu Cache lại và gửi qua `main_renderer.php` để vẽ ra HTML (danh sách bài tập) trả về màn hình cho sinh viên.

---

## 2. Mã nguồn thực tế tại Moodle

Dưới đây là sơ đồ mapping giữa luồng Pipeline và các file code thực tế đang được xây dựng:

### A. Tầng Giao tiếp API (`classes/api/client.php`)
Chịu trách nhiệm kết nối, truyền tải bảo mật và retry nếu gặp lỗi mạng.
```php
public function get_suggestions($userid, $courseid, $filters = []) {
    // Chỉ gửi các thông tin định danh cơ bản sang API
    $payload = [
        'user_id' => $userid,
        'course_id' => $courseid,
        'limit' => 10
    ];
    // Gọi POST request tới bên thứ 3
    return $this->send_request('/api/suggestions', 'POST', $payload);
}
```

### B. Tầng Nghiệp vụ & Tối ưu (`classes/services/exercise_service.php`)
Chịu trách nhiệm Caching để Moodle không bị lag, và Validation dữ liệu đầu vào/ra.
```php
public function get_suggestions($userid, $courseid, $filters = []) {
    $cachekey = "sug_{$userid}_{$courseid}";
    $cached = $this->cache->get($cachekey);
    
    // Nếu có cache trong 1 giờ qua -> Lấy dùng luôn
    if ($cached !== false) return $cached;

    // Nếu không có -> Gọi sang Client API
    $response = $this->client->get_suggestions($userid, $courseid, $filters);
    
    // Lưu cache để dùng cho các click sau
    $this->cache->set($cachekey, $response);
    return $response;
}
```

### C. Tầng Hiển thị (`classes/output/main_renderer.php`)
Chịu trách nhiệm biến cục mảng Data khô khan thành HTML giao diện xịn xò.
```php
public function render_suggestions($suggestions) {
    $html = '';
    foreach ($suggestions as $ex) {
        // Biến cục JSON thành các thẻ <div> giao diện đẹp mắt
        $html .= "<div class='exercise-card'>";
        $html .= "<b>" . htmlspecialchars($ex['title']) . "</b>";
        $html .= "</div>";
    }
    return $html;
}
```

---

## 3. Tại sao chọn kiến trúc này?
- **Tập trung vào "Món chính":** Chức năng quan trọng nhất của giao diện người dùng (hiển thị gợi ý Moodle) được đáp ứng tức thì và độ chính xác tuyệt đối từ bên Thứ 3.
- **Tốc độ:** Tận dụng tối đa `Cache API` của Moodle. Dù một lớp có 300 sinh viên cùng bấm "Gợi ý", Moodle cũng không bị sập hay chờ API bên thứ 3 phản hồi chậm.
- **Dễ bảo trì:** Logic gọi API và giao diện được tách biệt hoàn toàn làm 3 lớp (Client - Service - Renderer). Mọi nâng cấp (như thêm Món phụ - Push Data cho bên kìa xài) cũng không làm gián đoạn luồng Pull này.
