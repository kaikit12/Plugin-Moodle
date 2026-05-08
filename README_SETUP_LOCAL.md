# Hướng dẫn cài đặt Moodle local trên Windows (dùng XAMPP)

## 1. Cài đặt XAMPP
- Tải XAMPP tại: https://www.apachefriends.org/download.html
- Cài đặt XAMPP (chọn Apache, MySQL, PHP >= 7.4)
- Sau khi cài xong, mở XAMPP Control Panel, Start Apache và MySQL

## 2. Tải và giải nén Moodle
- Tải bản mới nhất tại: https://download.moodle.org/
- Giải nén vào thư mục: `C:\xampp\htdocs\moodle`

## 3. Tạo database cho Moodle
- Truy cập http://localhost/phpmyadmin
- Tạo database mới, ví dụ: `moodle`
- Chọn utf8mb4_unicode_ci

## 4. Cài đặt Moodle
- Truy cập http://localhost/moodle
- Làm theo hướng dẫn cài đặt:
  - Chọn ngôn ngữ, xác nhận các extension PHP
  - Nhập thông tin database (user: root, pass: để trống nếu mặc định XAMPP)
  - Thiết lập tài khoản admin, tên site
- Đợi quá trình cài đặt hoàn tất

## 5. Cài plugin local_exercise_suggestion
- Copy thư mục `local_exercise_suggestion` vào `C:\xampp\htdocs\moodle\local\`
- Truy cập http://localhost/moodle/admin để cài plugin
- Sau khi cài xong, truy cập http://localhost/moodle/local/exercise_suggestion/index.php để kiểm thử

## 6. Lưu ý
- Nếu gặp lỗi extension PHP, vào XAMPP Control Panel > Config > php.ini để bật các extension cần thiết (curl, intl, mbstring...)
- Nếu cài lại nhiều lần, xóa sạch thư mục `moodledata` và database cũ trước khi cài mới

## 7. Tài liệu tham khảo
- [Hướng dẫn cài Moodle trên Windows (chính thức)](https://docs.moodle.org/402/en/Windows_installation_using_XAMPP)
- [Cộng đồng Moodle Việt Nam](https://moodle.org/course/view.php?id=28)
