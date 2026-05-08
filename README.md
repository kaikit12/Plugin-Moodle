# Moodle Local Plugin: Exercise Suggestion

Plugin `local_exercise_suggestion` them chuc nang goi y bai tap va cham diem bai nop cho Moodle. Phien ban hien tai duoc toi uu cho demo: danh sach bai goi y lay tu API rieng, bai nop duoc cham qua grading API tren Render, va giao dien co popup chi tiet / popup dang cham de trai nghiem muot hon.

## Tinh nang hien tai

- Goi y bai tap theo sinh vien va khoa hoc.
- Map diem nang luc sang muc do bai tap hien co: `easy`, `medium`, `hard`.
- Neu khong co bai dung cap do, API ha ve cap gan nhat thap hon thay vi goi y lung tung.
- Trang danh sach co popup chi tiet bai tap, hien mo ta, yeu cau, tieu chi cham diem, muc do va thoi gian.
- Nut `Lam ngay` trong popup moi chuyen sang trang lam bai.
- Trang lam bai co code editor, test cases/tieu chi, autosave local.
- Khi bam nop bai, hien popup “dang cham diem” va khoa nut submit de tranh spam click.
- Bai nop duoc gui den grading API:
  `https://backend-ovru.onrender.com/submissions/`
- Trang ket qua hien diem, feedback AI, improvement suggestions, criteria details va test results.
- Trang danh sach hien ty le hoan thanh theo user/course dua tren cac bai da submit.

## Cau truc quan trong

```text
local_exercise_suggestion/
├── ajax.php
├── index.php
├── settings.php
├── start_api.ps1
├── classes/
│   ├── api/
│   │   ├── client.php
│   │   └── response_handler.php
│   └── services/
│       └── exercise_service.php
├── exercise_suggestion_api/
│   └── api_server.php
├── templates/
│   ├── suggestions_list.mustache
│   ├── exercise_view.mustache
│   └── result_view.mustache
└── lang/
    └── en/local_exercise_suggestion.php
```

## API dang dung

### 1. Suggestion API local

Dung de lay danh sach bai tap va chi tiet bai tap tu database `Data_PersonalizedSystem`.

Chay server:

```powershell
cd D:\Code\Moodle\local_exercise_suggestion
.\start_api.ps1
```

Mac dinh server chay tai:

```text
http://localhost:8080
```

Endpoints chinh:

- `POST /api/suggestions`
- `GET /api/exercise/{id}`

### 2. Grading API Render

Dung de cham bai nop va tra ve score/feedback:

```text
https://backend-ovru.onrender.com/submissions/
```

Plugin gui code len endpoint nay trong `classes/api/client.php`.

## Cai dat trong Moodle local

Vi du voi XAMPP:

```text
C:\xampp\htdocs\moodle\local\exercise_suggestion
```

Neu dang code o o D, co the copy plugin vao Moodle hoac cau hinh de Moodle load plugin tu dung duong dan dang phat trien. Trong code hien tai `index.php` va `ajax.php` co fallback load config:

```text
C:\xampp\htdocs\moodle\config.php
```

Sau khi sua template/PHP, neu Moodle van hien giao dien cu, purge cache:

```powershell
cd C:\xampp\htdocs\moodle
C:\xampp\php\php.exe admin\cli\purge_caches.php
```

## Cach demo nhanh

1. Start Apache/MySQL trong XAMPP.
2. Start suggestion API:

```powershell
cd D:\Code\Moodle\local_exercise_suggestion
.\start_api.ps1
```

3. Mo Moodle:

```text
http://localhost/moodle/local/exercise_suggestion/index.php?courseid=2&action=list
```

4. Bam `Xem chi tiet` tren mot bai tap.
5. Popup chi tiet hien ra, bam `Lam ngay`.
6. Viet/nop code.
7. Popup dang cham diem hien ra.
8. Khi grading API tra ket qua, Moodle chuyen sang trang diem va feedback.

## Luong xu ly

```text
Student
  -> Moodle list page
  -> Suggestion API local
  -> Popup chi tiet bai tap
  -> Trang lam bai
  -> Render grading API
  -> Trang ket qua / feedback
```

## Ghi chu ve completion

Bang progress cu trong plugin chua dung vi schema hien tai khong khop voi external exercise id. De tranh rui ro truoc demo, ty le hoan thanh dang duoc luu bang Moodle user preferences theo `user + course`.

Khi submit thanh cong:

- ma bai tap duoc luu vao preference cua user
- trang list tinh lai so bai da hoan thanh tren danh sach bai dang hien
- card da lam hien badge `XONG`

## Ghi chu ve DSA_Fusion_Backend

Thu muc `DSA_Fusion_Backend` khong con can cho flow hien tai vi plugin da chuyen sang grading API tren Render. Co the xoa khoi GitHub/repo neu khong dung nua.

## Cac file nen commit cho phien ban hien tai

```powershell
git add ajax.php classes/api/client.php classes/api/response_handler.php classes/services/exercise_service.php exercise_suggestion_api/api_server.php index.php templates/exercise_view.mustache templates/result_view.mustache templates/suggestions_list.mustache README.md start_api.ps1
```

Neu muon xoa backend/report cu:

```powershell
git rm -r -f --ignore-unmatch DSA_Fusion_Backend REVIEW_REPORT.md PROJECT_CONTEXT_FOR_AI.md "tổng quan plugin moodle"
```

## Luu y

- Khong dung `git add .` neu trong repo con file local khong lien quan.
- Neu giao dien Moodle khong doi sau khi sua template, purge cache.
- Neu suggestion API khong cap nhat, tat cua so server `start_api.ps1` va chay lai.
- Render API co the mat vai giay de wake up lan dau.
