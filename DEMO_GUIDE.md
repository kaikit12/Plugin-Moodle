# Hướng dẫn Cài đặt & Sử dụng Plugin `local_exercise_suggestion` (User Journey)

Tài liệu này mô tả chi tiết quá trình ứng dụng thực tế. 
Do **tính chất đặc thù của plugin là tiêu thụ dữ liệu (Consume Data)**, mọi logic phức tạp đã được AI phía đối tác xử lý. Plugin này mang đến cho giáo viên và sinh viên một trải nghiệm mượt mà, "bấm là có".

## 1. Dành cho Quản trị viên (Admin)
1. **Cài đặt Plugin**: Upload file ZIP `local_exercise_suggestion.zip` vào Moodle (Site administration > Plugins > Install plugins).
2. **Cấu hình Kết nối API**: Vào cấu hình riêng của plugin (Local plugins > Exercise Suggestion).
    - **API URL**: Nhập đường dẫn API do đối tác thứ 3 cung cấp (VD: `https://ai.partner.com`).
    - **API Key**: Mã bảo mật JWT hoặc Bearer Token để kết nối.
    - Cấu hình thời gian **Lưu Cache (phút)** để tối ưu tốc độ.
3. **Lưu lại** hệ thống sẵn sàng hoạt động.

## 2. Dành cho Giáo viên (Teacher)
Đơn giản tối đa! Giáo viên không cần cấu hình thuật toán phức tạp:
1. Vào khóa học của mình.
2. Thêm Activity hoặc Block "Gợi ý bài tập" vào trong giao diện khóa học.
3. Khóa học ngay lập tức đã sẵn sàng với hệ thống AI gợi ý của bên thứ 3.

## 3. Dành cho Sinh viên (Student)
1. Sinh viên vào Dashboard của khóa học.
2. Ở cuối mỗi bài học hoặc trên thanh Sidebar, sinh viên nhìn thấy nút lớn **"Gợi ý bài tập cá nhân hoá"**.
3. Click vào nút:
   - Hệ thống hiện Loading nhẹ (trong lúc này Moodle gọi API).
   - Danh sách bài tập đúng trình độ hiện ra ngạy dưới dạng thẻ (Cards) HTML thân thiện do Moodle render.

---

## Sơ đồ luồng tương tác (Mermaid Flowchart)

Sơ đồ tập trung thẳng vào luồng cốt lõi "Món chính": **Hiển thị giao diện & Fetch API.**

```mermaid
flowchart TD
    %% Định nghĩa các Actor & System
    Student([Sinh viên])
    UI[Giao diện Moodle\n(Browser)]
    ServiceLayer[Service & Cache Layer\n(Moodle Plugin)]
    APIClient[API Client\n(Moodle Plugin)]
    ThirdPartyAPI[((Hệ thống AI\nBên Thứ 3))]

    %% Hành trình người dùng
    subgraph Trải nghiệm Moodle (User Journey)
        Student -->|1. Bấm 'Gợi ý bài tập'| UI
        UI -->|2. Gọi AJAX request| ServiceLayer
    end

    %% Pipeline xử lý
    subgraph Data Pipeline Trọng Tâm
        ServiceLayer -->|3. Kiểm tra| CheckCache{Có\nCache?}
        CheckCache -->|Có (Nhanh)| CacheResult[Lấy Data từ Cache Moodle]
        CheckCache -->|Không có| APIClient
        
        APIClient -->|4. HTTP POST /api/suggestions\nKèm API KEY| ThirdPartyAPI
        ThirdPartyAPI -.->|5. Trả về JSON\nList bài tập| APIClient
        APIClient -->|6. Lưu vào| CacheResult
        
        CacheResult -->|7. Data| Renderer[Main Renderer html]
        Renderer -->|8. HTML UI Cards| UI
    end
    
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef actor fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px;
    class Student actor;
```
