# Test Cases (Kịch bản kiểm thử)

Dưới đây là bộ Test Cases chi tiết để nghiệm thu hệ thống AI Grader.

| TC ID | Module | Mô tả Test Case (Mục tiêu) | Các bước thực hiện (Steps) | Kết quả mong đợi (Expected Result) |
| :--- | :--- | :--- | :--- | :--- |
| **TC_01** | Frontend UI | Kiểm tra hiển thị nút FAB | 1. Đăng nhập Moodle với tk sinh viên.<br>2. Truy cập trang Dashboard. | Nút FAB màu xanh xuất hiện ở góc dưới bên phải màn hình. |
| **TC_02** | Frontend UI | Kiểm tra tính năng Modal | 1. Bấm vào nút FAB.<br>2. Chọn một khóa học (Ví dụ: KTLT). | Modal hiển thị hiệu ứng mượt mà, tải ra danh sách 5 bài tập gợi ý. Không lỗi JS console. |
| **TC_03** | Frontend UI | Kiểm tra chống Spam Submit | 1. Mở 1 bài tập, nhập code.<br>2. Bấm nút Submit liên tục (Double click). | Nút Submit mờ đi (disabled) ngay sau click đầu tiên, đổi text thành "Đang chấm...". Không có duplicate request gửi đi. |
| **TC_04** | Backend API | Kiểm tra Gợi ý bài tập (Mock API) | 1. Gọi `ajax.php?action=get_suggestions` với `course_id=2` (KTLT). | Trả về JSON chứa mảng `suggestions` với 5 bài tập. HTTP Code 200. Điểm khó ánh xạ đúng với điểm trên Supabase. |
| **TC_05** | Backend AI | Nộp Code hoàn chỉnh (Happy Path) | 1. Điền code Python chuẩn xác giải quyết bài toán.<br>2. Bấm Submit. | Hệ thống trả về Score 100, các test cases đều Passed (`AC`), Feedback của AI khen ngợi và phân tích độ phức tạp thuật toán. |
| **TC_06** | Backend AI | Nộp Code sai logic / cú pháp | 1. Điền code sai cú pháp (vd thiếu dấu `:` trong Python) hoặc sai công thức tính toán.<br>2. Bấm Submit. | Hệ thống bắt được lỗi, Score thấp (vd: 0-30), test case Failed, AI chỉ ra chính xác dòng code bị lỗi và đưa gợi ý sửa (Hints). |
| **TC_07** | Backend AI | Kiểm tra tính năng Dự phòng (AST Fallback) | 1. Đổi tên mô hình trong `.env` thành `gemini-loi-khong-ton-tai`.<br>2. Nộp bài tập. | Hệ thống KHÔNG sập. Tự động chấm bằng AST. Dòng nhận xét hiện: *"Hệ thống đã chấm điểm bằng thuật toán (không có nhận xét chi tiết cho test case này)."* |
| **TC_08** | Moodle Cache | Kiểm thử Cache Miss và Hit | 1. Nộp bài, xem kết quả xong (Cache Miss 1st time, set Cache).<br>2. F5 tải lại trang Kết quả ngay lập tức. | Thời gian tải trang cực nhanh (<100ms). Giao diện không hiện dòng log kỹ thuật nào. Mock API Server không bị gọi lại. |
| **TC_09** | Security | Truy cập trái phép API | 1. Mở Tab Ẩn danh (chưa đăng nhập Moodle).<br>2. Truy cập thẳng URL `local/exercise_suggestion/ajax.php?action=get_suggestions`. | Trả về màn hình lỗi bắt buộc đăng nhập (Require Login) hoặc thông báo truy cập bị từ chối. |
| **TC_10** | Database | Ghi log hệ thống | 1. Hoàn thành 1 chu trình Nộp bài.<br>2. Mở DB Moodle, kiểm tra bảng `mdl_local_exsug_logs`. | Có record mới chứa đúng UserID (số nguyên), Action = `submit`, HTTP Status = `200`. Không bị lỗi `Incorrect integer value`. |
