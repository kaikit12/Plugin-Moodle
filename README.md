# Exercise Suggestion Integration Plugin for Moodle

Plugin Moodle tích hợp với hệ thống API bên thứ 3 để cung cấp gợi ý bài tập thông minh dựa trên phân tích học tập của sinh viên.

## Tính năng chính

- **Tích hợp API**: Kết nối với hệ thống gợi ý bài tập bên ngoài
- **Gợi ý thông minh**: Đưa ra bài tập phù hợp dựa trên tiến độ học tập
- **Phân tích học tập**: Thu thập và hiển thị analytics từ API
- **Hệ thống feedback**: Cho phép sinh viên đánh giá bài tập
- **Cache tối ưu**: Lưu trữ tạm thời để cải thiện hiệu năng
- **Logging**: Ghi nhận hoạt động để phân tích và debug

## Cấu trúc thư mục

```
local_exercise_suggestion/
├── classes/
│   ├── api/
│   │   ├── client.php              # API client class
│   │   └── response_handler.php    # Xử lý response từ API
│   └── services/
│       └── exercise_service.php    # Business logic layer
├── db/
│   ├── access.php                  # Định nghĩa capabilities
│   ├── install.xml                 # Database schema
│   └── upgrade.php                 # Database upgrade script
├── lang/
│   └── en/
│       └── local_exercise_suggestion.php  # Language strings
├── tests/
│   ├── api_test.php               # Unit tests cho API classes
│   └── services_test.php          # Unit tests cho services
├── lib.php                        # Library functions
├── settings.php                   # Admin settings
├── version.php                    # Plugin version info
└── README.md                      # Tài liệu này
```

## Yêu cầu hệ thống

- Moodle 3.10 trở lên
- PHP 7.4 trở lên
- cURL extension được bật
- Kết nối internet để gọi API bên ngoài

## Cài đặt

### Bước 1: Copy plugin vào Moodle

```bash
# Đi đến thư mục Moodle
cd /path/to/your/moodle

# Copy plugin vào thư mục local
cp -r local_exercise_suggestion local/exercise_suggestion/
```

### Bước 2: Cài đặt qua Moodle Admin

1. Đăng nhập vào Moodle với quyền Site Administrator
2. Truy cập **Site administration** → **Notifications**  
3. Moodle sẽ phát hiện plugin mới và yêu cầu cài đặt
4. Nhấn **"Upgrade Moodle database now"**

### Bước 3: Cấu hình plugin

1. Truy cập **Site administration** → **Plugins** → **Local plugins** → **Exercise Suggestion Integration**
2. Cấu hình các thông số:
   - **API Base URL**: URL của API bên thứ 3
   - **API Key**: Key xác thực
   - **API Timeout**: Thời gian timeout (mặc định 30s)
   - **Enable Analytics**: Bật/tắt tính năng analytics
   - **Enable Feedback**: Bật/tắt thu thập feedback
   - **Cache Duration**: Thời gian lưu cache (mặc định 1 giờ)

## Sử dụng

### Cho Admin

1. **Cấu hình API**: Vào Settings để nhập thông tin API
2. **Test kết nối**: Sử dụng tính năng test để kiểm tra API
3. **Quản lý quyền**: Phân quyền xem suggestions cho các vai trò
4. **Theo dõi logs**: Xem báo cáo hoạt động trong database

### Cho Giáo viên

1. **Xem suggestions của sinh viên**: Truy cập khóa học → Exercise Suggestions
2. **Phân tích tiến độ**: Xem analytics của cả lớp
3. **Quản lý feedback**: Theo dõi đánh giá của sinh viên

### Cho Sinh viên

1. **Nhận gợi ý bài tập**: Xem danh sách bài tập được gợi ý
2. **Lọc theo tiêu chí**: Sử dụng filter theo độ khó, chủ đề
3. **Đánh giá bài tập**: Cung cấp feedback về bài tập
4. **Theo dõi tiến độ**: Xem analytics cá nhân

## API Documentation

### Client Class (`\local_exercise_suggestion\api\client`)

```php
// Khởi tạo client
$client = new client($apiUrl, $apiKey, $timeout);

// Lấy gợi ý bài tập
$suggestions = $client->get_exercise_suggestions($userId, $courseId, $filters);

// Gửi feedback
$result = $client->submit_exercise_feedback($exerciseId, $userId, $feedback);

// Test kết nối
$status = $client->test_connection();
```

### Service Class (`\local_exercise_suggestion\services\exercise_service`)

```php
// Khởi tạo service
$service = new exercise_service();

// Lấy gợi ý cho sinh viên
$result = $service->get_suggestions_for_user($userId, $courseId, $filters);

// Gửi feedback
$result = $service->submit_feedback($exerciseId, $userId, $feedbackData);

// Lấy analytics
$analytics = $service->get_user_analytics($userId, $courseId);
```

## Database Tables

Plugin tạo 5 bảng trong database (đã rút gọn tên để phù hợp giới hạn 28 ký tự của Moodle):

1. **local_exsug_logs**: Log các request và response
2. **local_exsug_feedback**: Lưu feedback từ sinh viên  
3. **local_exsug_cache**: Cache suggestions để tăng hiệu năng
4. **local_exsug_progress**: Theo dõi tiến độ học tập
5. **local_exsug_analytics**: Cache dữ liệu analytics

## Troubleshooting

### Lỗi kết nối API

```bash
# Kiểm tra kết nối
curl -H "Authorization: Bearer YOUR_API_KEY" https://your-api-url/health

# Kiểm tra cURL trong PHP
php -m | grep curl
```

### Lỗi cấu hình

1. Kiểm tra API URL và key trong Settings
2. Đảm bảo server có thể truy cập internet
3. Kiểm tra firewall không block outbound connections

### Lỗi permissions

1. Kiểm tra capabilities trong **Users** → **Permissions** → **Define roles**
2. Đảm bảo sinh viên được enroll vào khóa học
3. Kiểm tra context level của capabilities

### Debug mode

Bật debug mode trong plugin settings để xem chi tiết:

```php
// Trong config.php
$CFG->debug = E_ALL;
$CFG->debugdisplay = 1;
```

## Testing

Chạy unit tests:

```bash
# Từ thư mục Moodle root
php admin/tool/phpunit/cli/init.php
vendor/bin/phpunit local/exercise_suggestion/tests/
```

## Bảo mật

- API keys được mã hóa trong database
- Validate tất cả input từ API
- Sử dụng prepared statements cho database queries
- Kiểm tra permissions trước khi truy cập dữ liệu

## Performance

- Sử dụng cache để giảm API calls
- Background tasks cho sync dữ liệu
- Database indexes cho query nhanh
- Configurable timeouts

## Changelog

### Version 1.0.0 (2024-10-22)
- Initial release
- API integration với external exercise system
- Basic suggestions và feedback functionality
- Analytics integration
- Caching và performance optimization

## Support

Để được hỗ trợ, vui lòng:

1. Kiểm tra tài liệu này trước
2. Xem logs trong Moodle admin
3. Liên hệ team phát triển với thông tin chi tiết về lỗi

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Plugin này được phát hành dưới GNU General Public License v3.0.