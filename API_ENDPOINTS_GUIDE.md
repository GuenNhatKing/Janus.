# PBL6 Backend API — Endpoint and Request Guide

Tài liệu này được đối chiếu với FastAPI application hiện tại, Pydantic schemas,
dependencies, OpenAPI runtime tại `http://127.0.0.1:8000/openapi.json` và các
test Pytest/Newman local. Đây là tài liệu cho Backend; không phải tài liệu URL
Frontend hay kết nối trực tiếp đến PostgreSQL.

## 1. Thông tin chung

- Base URL local: `http://127.0.0.1:8000`
- API prefix: `/api/v1`
- Backend: FastAPI
- Authentication: JWT Bearer token
- Token hết hạn theo `ACCESS_TOKEN_EXPIRE_MINUTES`, mặc định trong code là 30 phút.
- Role hợp lệ: `user`, `moderator`, `admin`.
- Video hiện chỉ nhận MP4, tối đa 50 MiB, lưu local trong `UPLOAD_DIR`.
- AI: `run_video_analysis` gọi pipeline NSFW-Detection (Adult) qua subprocess;
  nếu môi trường AI chưa sẵn sàng thì job ghi lý do và dùng kết quả mock.
  Không gọi Cloud Storage hoặc API AI bên ngoài.
- 37 operation hoạt động (không còn route `501`): 19 endpoint cũ và 18 endpoint
  triển khai mới — logout/refresh/password reset, cập nhật profile, streaming,
  tìm kiếm theo nhãn, xác nhận/sửa nhãn, appeal, quản lý nhãn/video và thống kê
  (chi tiết mục 3.20).
- Refresh token và token đặt lại mật khẩu chỉ lưu dạng băm SHA-256; access
  token mang `jti` nên đăng xuất thu hồi được ngay.

### Trạng thái xác minh

- **Đã test**: đã có request thực tế trong collection Newman hoặc test Pytest.
- **Code/OpenAPI**: route và schema đã được đối chiếu, nhưng chưa có request
  runtime riêng chứng minh đầy đủ hành vi đó.
- Không coi route Code/OpenAPI là bằng chứng nghiệp vụ đầy đủ.

## 2. Quy tắc request chung

### JWT

Đăng nhập bằng `POST /api/v1/auth/login`, lấy trường `access_token`, sau đó gửi:

```http
Authorization: Bearer <access_token>
```

Token được ký HS256, chứa `sub`, `role` và `exp`. Backend tra cứu user theo
`sub` và kiểm tra `is_active`. Token không hợp lệ, thiếu, hết hạn hoặc user
không còn hợp lệ trả HTTP `401`.

Không có cơ chế logout/revoke token hoặc refresh token trong code hiện tại.

### Lỗi validation

FastAPI/Pydantic trả HTTP `422` khi JSON, UUID, file field hoặc validation
không hợp lệ. Lỗi nghiệp vụ dùng JSON dạng:

```json
{
  "detail": "Thông báo lỗi"
}
```

### Upload file

Trong Postman chọn **Body → form-data**, tạo field `file`, đổi type của field
thành **File**, rồi chọn file MP4. Không tự đặt `Content-Type` khi dùng
multipart; Postman phải tự thêm boundary. `caption` là query parameter, không
phải multipart field:

```text
POST /api/v1/videos?caption=My%20caption
```

## 3. Endpoint chi tiết

### 3.1 Health check

**Thông tin chung**

- Method: `GET`
- Path: `/health`
- Operation ID: `health`
- Full URL mẫu: `http://127.0.0.1:8000/health`
- Chức năng: kiểm tra Backend còn phản hồi.
- Module: System
- Authentication: Không yêu cầu
- Role/permission: Không có
- Content-Type: Không có request body
- Trạng thái xác minh: **Đã test** — health trả HTTP `200`.

**A. Path parameters**: Không có.

**B. Query parameters**: Không có.

**C. Headers**: Không bắt buộc.

**D. Request body**: Không có.

**E. Response mẫu**

```json
{"status": "ok"}
```

HTTP `200`.

**F. Lỗi thường gặp**

- Không kết nối được: Backend chưa chạy, sai host/port hoặc firewall.
- HTTP `5xx`: lỗi khởi động/runtime; không có response nghiệp vụ riêng được
  định nghĩa trong endpoint.

**G. Ví dụ gọi API**

```bash
curl http://127.0.0.1:8000/health
```

### 3.2 Đăng ký tài khoản

**Thông tin chung**

- Method: `POST`
- Path: `/api/v1/auth/register`
- Operation ID: `register`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/auth/register`
- Chức năng: tạo user mới.
- Module: Auth
- Authentication: Không yêu cầu
- Role/permission: User mới mặc định có role `user`.
- Content-Type: `application/json`
- Trạng thái xác minh: **Đã test** — Auth Newman trả `201`; duplicate trả `409`.

**A. Path parameters**: Không có.

**B. Query parameters**: Không có.

**C. Headers**

```http
Content-Type: application/json
```

**D. Request body**

```json
{
  "email": "user@example.com",
  "display_name": "Example User",
  "password": "password123"
}
```

| Trường | Kiểu | Bắt buộc | Quy tắc |
|---|---|---:|---|
| `email` | string/email | Có | Email hợp lệ; lưu dạng lowercase |
| `display_name` | string | Có | 1–120 ký tự |
| `password` | string | Có | 8–128 ký tự |

**E. Response mẫu**

```json
{
  "id": "00000000-0000-0000-0000-000000000001",
  "email": "user@example.com",
  "display_name": "Example User",
  "role": "user"
}
```

HTTP `201`.

**F. Lỗi thường gặp**

- `409`: email đã được sử dụng.
- `422`: email, display name hoặc password không đúng schema.
- `5xx`: database không khả dụng hoặc lỗi commit.

**G. Ví dụ gọi API**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"user@example.com\",\"display_name\":\"Example User\",\"password\":\"password123\"}"
```

### 3.3 Đăng nhập

**Thông tin chung**

- Method: `POST`
- Path: `/api/v1/auth/login`
- Operation ID: `login`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/auth/login`
- Chức năng: xác thực email/password và cấp access token.
- Module: Auth
- Authentication: Không yêu cầu
- Role/permission: Không có
- Content-Type: `application/json`
- Trạng thái xác minh: **Đã test** — Auth/Newman login trả `200`.

**A. Path parameters**: Không có.

**B. Query parameters**: Không có.

**C. Headers**

```http
Content-Type: application/json
```

**D. Request body**

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

| Trường | Kiểu | Bắt buộc | Quy tắc |
|---|---|---:|---|
| `email` | string/email | Có | Email hợp lệ |
| `password` | string | Có | Không có min/max riêng trong `LoginRequest` |

**E. Response mẫu**

```json
{
  "access_token": "<access_token_from_this_response>",
  "token_type": "bearer"
}
```

HTTP `200`. Không ghi token thật vào tài liệu hoặc source control.

**F. Lỗi thường gặp**

- `401`: email không tồn tại hoặc password sai.
- `422`: email sai định dạng hoặc thiếu field.

**G. Ví dụ gọi API**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"user@example.com\",\"password\":\"password123\"}"
```

Trong Postman lưu `access_token` từ response vào collection/environment
variable, không hardcode token đã hết hạn.

### 3.4 Xem hồ sơ hiện tại

**Thông tin chung**

- Method: `GET`
- Path: `/api/v1/profile`
- Operation ID: `profile`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/profile`
- Chức năng: trả user của JWT hiện tại.
- Module: User Profile
- Authentication: Bắt buộc Bearer JWT
- Role/permission: User active; mọi role hợp lệ đều được gọi.
- Content-Type: Không có body
- Trạng thái xác minh: **Đã test** — User Profile collection.

**A/B. Path và query parameters**: Không có.

**C. Headers**

```http
Authorization: Bearer <access_token>
```

**D. Request body**: Không có.

**E. Response mẫu**

```json
{
  "id": "00000000-0000-0000-0000-000000000001",
  "email": "user@example.com",
  "display_name": "Example User",
  "role": "user"
}
```

HTTP `200`.

**F. Lỗi thường gặp**

- `401`: thiếu, sai, hết hạn hoặc không xác thực được JWT.

**G. Ví dụ gọi API**

```bash
curl http://127.0.0.1:8000/api/v1/profile ^
  -H "Authorization: Bearer <access_token>"
```

### 3.5 Upload video

**Thông tin chung**

- Method: `POST`
- Path: `/api/v1/videos`
- Operation ID: `upload_video`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/videos?caption=Demo`
- Chức năng: lưu video local, tạo AI job mock và trả metadata video.
- Module: Video Upload
- Authentication: Bắt buộc Bearer JWT
- Role/permission: User active; không yêu cầu moderator/admin.
- Content-Type: `multipart/form-data`
- Trạng thái xác minh: **Đã test** — video thật, Pytest và Newman.

**A. Path parameters**: Không có.

**B. Query parameters**

| Tham số | Kiểu | Bắt buộc | Mặc định | Ý nghĩa |
|---|---|---:|---|---|
| `caption` | string hoặc null | Không | `null` | Caption video; truyền trên URL |

**C. Headers**

```http
Authorization: Bearer <access_token>
```

Không tự thêm `Content-Type`; client tạo multipart boundary.

**D. Request body**

Body → form-data:

| Field | Type | Bắt buộc | Quy tắc |
|---|---|---:|---|
| `file` | File | Có | Tên file `.mp4`, MIME `video/mp4`, MP4 magic bytes/brand/codec hợp lệ |

Giới hạn kích thước là 50 MiB (`50 * 1024 * 1024`). Backend kiểm tra marker
codec `avc1`, `hvc1`, `hev1`, `av01` hoặc `mp4v`.

**E. Response mẫu**

```json
{
  "id": "00000000-0000-0000-0000-000000000002",
  "original_filename": "Travel_4.mp4",
  "caption": "Demo",
  "size_bytes": 2609079,
  "status": "processing",
  "created_at": "2026-10-25T15:00:00Z"
}
```

HTTP `201`. Background mock analysis có thể chuyển status thành `published`
và tạo kết quả AI sau khi request hoàn tất.

**F. Lỗi thường gặp**

- `400`: không phải `.mp4`, MIME khác `video/mp4`, magic bytes/brand/codec không
  hợp lệ.
- `401`: thiếu hoặc sai JWT.
- `413`: vượt quá 50 MiB.
- `422`: thiếu field file hoặc request multipart sai.
- `5xx`: lỗi lưu file/database.

**G. Ví dụ gọi API**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/videos?caption=Demo" ^
  -H "Authorization: Bearer <access_token>" ^
  -F "file=@local/TestDataset-v2/Adult/Adult (1).mp4;type=video/mp4"
```

### 3.6 Liệt kê video của tôi

**Thông tin chung**

- Method: `GET`
- Path: `/api/v1/videos`
- Operation ID: `list_my_videos`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/videos`
- Chức năng: liệt kê video chưa bị soft-delete của user hiện tại.
- Module: Video Management
- Authentication: Bắt buộc Bearer JWT
- Role/permission: Chỉ video thuộc user trong token.
- Content-Type: Không có body
- Trạng thái xác minh: **Đã test** — Video Management collection.

**A/B. Path và query parameters**: Không có. Chưa có pagination/search/filter.

**C. Headers**

```http
Authorization: Bearer <access_token>
```

**D. Request body**: Không có.

**E. Response mẫu**

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000002",
    "original_filename": "Travel_4.mp4",
    "caption": null,
    "size_bytes": 2609079,
    "status": "published",
    "created_at": "2026-10-25T15:00:00Z"
  }
]
```

HTTP `200`; có thể là `[]`.

**F. Lỗi thường gặp**: `401` khi thiếu/sai JWT.

**G. Ví dụ gọi API**

```bash
curl http://127.0.0.1:8000/api/v1/videos ^
  -H "Authorization: Bearer <access_token>"
```

### 3.7 Public feed

**Thông tin chung**

- Method: `GET`
- Path: `/api/v1/feed`
- Operation ID: `feed`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/feed`
- Chức năng: liệt kê tối đa 50 video `published`, chưa bị xóa.
- Module: Video Management
- Authentication: Không yêu cầu
- Role/permission: Không có
- Content-Type: Không có body
- Trạng thái xác minh: **Đã test** — Video Management collection.

**A/B. Path và query parameters**: Không có.

**C. Headers**: Không bắt buộc.

**D. Request body**: Không có.

**E. Response mẫu**: Cùng cấu trúc mỗi phần tử với `VideoResponse` ở mục 3.6.
HTTP `200`; có thể là `[]`.

**F. Lỗi thường gặp**: lỗi kết nối database có thể gây `5xx`; không có lỗi
nghiệp vụ riêng trong endpoint.

**G. Ví dụ gọi API**

```bash
curl http://127.0.0.1:8000/api/v1/feed
```

### 3.8 Xem kết quả AI của video

**Thông tin chung**

- Method: `GET`
- Path: `/api/v1/videos/{video_id}/ai`
- Operation ID: `ai_result`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/videos/<video_id>/ai`
- Chức năng: đọc AI job, transcript và labels.
- Module: AI Analysis
- Authentication: Bắt buộc Bearer JWT
- Role/permission: Owner, moderator hoặc admin.
- Content-Type: Không có body
- Trạng thái xác minh: **Đã test** — AI Analysis collection.

**A. Path parameters**

| Tham số | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---:|---|
| `video_id` | UUID | Có | ID video cần đọc |

**B. Query parameters**: Không có.

**C. Headers**

```http
Authorization: Bearer <access_token>
```

**D. Request body**: Không có.

**E. Response mẫu**

Khi NSFW-Detection chạy thật và phát hiện vi phạm Adult (video chuyển
sang `pending_review`):

```json
{
  "video_id": "00000000-0000-0000-0000-000000000002",
  "job_status": "succeeded",
  "transcript": "[NSFW-Detection] phán quyết: ADULT | độ tin cậy: 0.87 | anchor đã đánh giá: 12 | fps: 30.0\n[Speech-to-Text] chưa được triển khai — chưa có transcript âm thanh.",
  "labels": [
    {
      "name": "Adult",
      "confidence": 0.87,
      "level": "HIGH"
    }
  ]
}
```

Khi môi trường AI chưa sẵn sàng và `AI_ANALYSIS_MODE=auto`, job ghi rõ lý do
và dùng kết quả mock (đã xác minh runtime với Neon):

```json
{
  "video_id": "00000000-0000-0000-0000-000000000002",
  "job_status": "succeeded",
  "transcript": "[NSFW-Detection chưa sẵn sàng: chưa cài thư viện: tensorflow, torch, cv2, numpy]\nMock transcript for development testing.",
  "labels": [
    {
      "name": "Safe",
      "confidence": 0.95,
      "level": "HIGH"
    }
  ]
}
```

HTTP `200`. Với `AI_ANALYSIS_MODE=required` và môi trường AI chưa sẵn sàng,
`job_status` là `failed` và `job.error_message` chứa lý do.

**F. Lỗi thường gặp**

- `401`: thiếu/sai JWT.
- `404`: video không tồn tại, đã xóa hoặc không thuộc owner và caller không
  phải moderator/admin.
- `422`: `video_id` không phải UUID.

**G. Ví dụ gọi API**

```bash
curl http://127.0.0.1:8000/api/v1/videos/<video_id>/ai ^
  -H "Authorization: Bearer <access_token>"
```

### 3.9 Soft-delete video

**Thông tin chung**

- Method: `DELETE`
- Path: `/api/v1/videos/{video_id}`
- Operation ID: `delete_video`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/videos/<video_id>`
- Chức năng: đánh dấu video đã xóa, không xóa bản ghi ngay.
- Module: Video Management
- Authentication: Bắt buộc Bearer JWT
- Role/permission: Chỉ owner của video.
- Content-Type: Không có body
- Trạng thái xác minh: **Đã test** — ownership và soft-delete trong collection.

**A. Path parameters**: `video_id` — UUID, bắt buộc.

**B. Query parameters**: Không có.

**C. Headers**

```http
Authorization: Bearer <access_token>
```

**D. Request body**: Không có.

**E. Response**: HTTP `204 No Content`, không có JSON body.

**F. Lỗi thường gặp**

- `401`: thiếu/sai JWT.
- `404`: video không tồn tại hoặc caller không phải owner.
- `422`: video ID không hợp lệ.

**G. Ví dụ gọi API**

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/videos/<video_id> ^
  -H "Authorization: Bearer <access_token>"
```

### 3.10 Tạo content report

**Thông tin chung**

- Method: `POST`
- Path: `/api/v1/videos/{video_id}/reports`
- Operation ID: `create_report`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/videos/<video_id>/reports`
- Chức năng: báo cáo video vi phạm.
- Module: Content Report
- Authentication: Bắt buộc Bearer JWT
- Role/permission: User active; không yêu cầu moderator/admin.
- Content-Type: `application/json`
- Trạng thái xác minh: **Đã test** — Content Report collection.

**A. Path parameters**: `video_id` — UUID, bắt buộc.

**B. Query parameters**: Không có.

**C. Headers**

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

**D. Request body**

```json
{"reason": "Content violates local moderation policy"}
```

| Trường | Kiểu | Bắt buộc | Quy tắc |
|---|---|---:|---|
| `reason` | string | Có | 3–1000 ký tự |

**E. Response mẫu**

```json
{
  "id": "00000000-0000-0000-0000-000000000003",
  "video_id": "00000000-0000-0000-0000-000000000002",
  "reason": "Content violates local moderation policy",
  "status": "open"
}
```

HTTP `201`. Nếu video đang `published`, endpoint chuyển video sang
`pending_review`.

**F. Lỗi thường gặp**

- `401`: thiếu/sai JWT.
- `404`: video không tồn tại hoặc đã soft-delete.
- `409`: user đã có report `open` cho video này.
- `422`: thiếu reason hoặc reason ngoài giới hạn.

**G. Ví dụ gọi API**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/videos/<video_id>/reports ^
  -H "Authorization: Bearer <access_token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"reason\":\"Content violates local moderation policy\"}"
```

### 3.11 Moderation queue

**Thông tin chung**

- Method: `GET`
- Path: `/api/v1/moderation/queue`
- Operation ID: `moderation_queue`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/moderation/queue`
- Chức năng: liệt kê video `pending_review`, chưa bị xóa.
- Module: Moderation
- Authentication: Bắt buộc Bearer JWT
- Role/permission: `moderator` hoặc `admin`.
- Content-Type: Không có body
- Trạng thái xác minh: **Đã test** — Moderation collection.

**A/B. Path và query parameters**: Không có.

**C. Headers**

```http
Authorization: Bearer <moderator_or_admin_token>
```

**D. Request body**: Không có.

**E. Response**: HTTP `200`, mảng `VideoResponse`; có thể là `[]`.

**F. Lỗi thường gặp**

- `401`: thiếu/sai JWT.
- `403`: user không có role moderator/admin.

**G. Ví dụ gọi API**

```bash
curl http://127.0.0.1:8000/api/v1/moderation/queue ^
  -H "Authorization: Bearer <moderator_or_admin_token>"
```

### 3.12 Quyết định trạng thái video

**Thông tin chung**

- Method: `POST`
- Path: `/api/v1/moderation/videos/{video_id}/decision`
- Operation ID: `moderation_decision`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/moderation/videos/<video_id>/decision`
- Chức năng: moderator/admin approve hoặc reject video.
- Module: Moderation
- Authentication: Bắt buộc Bearer JWT
- Role/permission: `moderator` hoặc `admin`.
- Content-Type: `application/json`
- Trạng thái xác minh: **Code/OpenAPI** — route/schema đã đối chiếu; chưa có
  request Newman riêng cho endpoint này.

**A. Path parameters**: `video_id` — UUID, bắt buộc.

**B. Query parameters**: Không có.

**C. Headers**

```http
Authorization: Bearer <moderator_or_admin_token>
Content-Type: application/json
```

**D. Request body**

```json
{
  "action": "approve",
  "reason": "Review completed"
}
```

| Trường | Kiểu | Bắt buộc | Giá trị |
|---|---|---:|---|
| `action` | enum | Có | `approve` hoặc `reject` |
| `reason` | string/null | Không | Tối đa 1000 ký tự; mặc định `null` |

`approve` chuyển video sang `published`; action khác hợp lệ là `reject`, chuyển
sang `rejected`. Endpoint lưu `ModerationReview`.

**E. Response**: HTTP `204 No Content`.

**F. Lỗi thường gặp**

- `401`: thiếu/sai JWT.
- `403`: không phải moderator/admin.
- `404`: video không tồn tại hoặc đã xóa.
- `422`: UUID hoặc action/reason sai schema.

**G. Ví dụ gọi API**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/moderation/videos/<video_id>/decision ^
  -H "Authorization: Bearer <moderator_or_admin_token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"action\":\"approve\",\"reason\":\"Review completed\"}"
```

### 3.13 Danh sách report mở

**Thông tin chung**

- Method: `GET`
- Path: `/api/v1/moderation/reports`
- Operation ID: `moderation_reports`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/moderation/reports`
- Chức năng: liệt kê report có status `open`.
- Module: Moderation
- Authentication: Bắt buộc Bearer JWT
- Role/permission: `moderator` hoặc `admin`.
- Content-Type: Không có body
- Trạng thái xác minh: **Đã test** — Moderation collection.

**A/B. Path và query parameters**: Không có.

**C. Headers**

```http
Authorization: Bearer <moderator_or_admin_token>
```

**D. Request body**: Không có.

**E. Response**: HTTP `200`, mảng `ReportResponse`; có thể là `[]`.

**F. Lỗi thường gặp**

- `401`: thiếu/sai JWT.
- `403`: không phải moderator/admin.

**G. Ví dụ gọi API**

```bash
curl http://127.0.0.1:8000/api/v1/moderation/reports ^
  -H "Authorization: Bearer <moderator_or_admin_token>"
```

### 3.14 Quyết định report

**Thông tin chung**

- Method: `POST`
- Path: `/api/v1/moderation/reports/{report_id}/decision`
- Operation ID: `report_decision`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/moderation/reports/<report_id>/decision`
- Chức năng: xử lý một report đang mở và cập nhật video liên quan.
- Module: Moderation
- Authentication: Bắt buộc Bearer JWT
- Role/permission: `moderator` hoặc `admin`.
- Content-Type: `application/json`
- Trạng thái xác minh: **Đã test** — Moderation collection với approve và
  kiểm tra xử lý lặp.

**A. Path parameters**: `report_id` — UUID, bắt buộc.

**B. Query parameters**: Không có.

**C. Headers**

```http
Authorization: Bearer <moderator_or_admin_token>
Content-Type: application/json
```

**D. Request body**

```json
{
  "action": "approve",
  "reason": "Policy violation confirmed"
}
```

`action` nhận `approve` hoặc `reject`; `reason` nullable, tối đa 1000 ký tự.
Theo implementation hiện tại, `approve` làm video `rejected` và report
`rejected`; `reject` làm video `published` và report `resolved`. Cách đặt tên
action này là behavior thực tế của code, cần được Frontend tích hợp đúng.

**E. Response**: HTTP `204 No Content`.

**F. Lỗi thường gặp**

- `401`: thiếu/sai JWT.
- `403`: không phải moderator/admin.
- `404`: report không tồn tại, report không còn `open`, hoặc video liên quan
  không tồn tại.
- `422`: UUID hoặc body sai schema.

**G. Ví dụ gọi API**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/moderation/reports/<report_id>/decision ^
  -H "Authorization: Bearer <moderator_or_admin_token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"action\":\"approve\",\"reason\":\"Policy violation confirmed\"}"
```

### 3.15 Admin list/search users

**Thông tin chung**

- Method: `GET`
- Path: `/api/v1/admin/users`
- Operation ID: `admin_list_users`
- Full URL mẫu: `http://127.0.0.1:8000/api/v1/admin/users?search=Managed`
- Chức năng: Admin xem danh sách user và tìm theo email/display name.
- Module: Admin Management
- Authentication: Bearer JWT
- Role/permission: `admin`
- Trạng thái xác minh: **Đã test** — Admin Management Newman.

**Parameters and headers**

- Query `search`: string, không bắt buộc; tìm theo `email` hoặc `display_name`.
- Không có path parameter hoặc request body.
- Header: `Authorization: Bearer <admin_token>`.

**Response và lỗi**

- HTTP `200`, mảng user summary gồm `id`, `display_name`, `role`, `is_active`,
  `created_at`.
- `401` token thiếu/sai hoặc user inactive; `403` không phải admin.

```bash
curl "http://127.0.0.1:8000/api/v1/admin/users?search=Managed" ^
  -H "Authorization: Bearer <admin_token>"
```

### 3.16 Admin xem chi tiết user

- Method: `GET`
- Path: `/api/v1/admin/users/{user_id}`
- Operation ID: `admin_get_user`
- Authentication: Bearer JWT, role `admin`
- Response: HTTP `200`, gồm summary và `email`.
- Path `user_id`: UUID, bắt buộc.
- Request body/query: Không có.
- Lỗi: `401`, `403`, `404` nếu user không tồn tại, hoặc `422` nếu UUID sai.
- Trạng thái xác minh: **Đã test** — Admin Management Newman.

```bash
curl http://127.0.0.1:8000/api/v1/admin/users/<user_id> ^
  -H "Authorization: Bearer <admin_token>"
```

### 3.17 Admin khóa hoặc mở user

- Method: `PATCH`
- Path: `/api/v1/admin/users/{user_id}/status`
- Operation ID: `admin_update_user_status`
- Authentication: Bearer JWT, role `admin`
- Path `user_id`: UUID, bắt buộc.
- Content-Type: `application/json`
- Body: `{"is_active": false}` hoặc `{"is_active": true}`; `is_active` bắt buộc
  là boolean.
- Response: HTTP `200`, user detail sau cập nhật.
- Lỗi: `400` nếu admin tự khóa chính mình; `401`, `403`, `404`, `422` theo auth,
  quyền, ID và schema.
- Trạng thái xác minh: **Đã test** — Admin Management Newman.

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/admin/users/<user_id>/status ^
  -H "Authorization: Bearer <admin_token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"is_active\":false}"
```

### 3.18 Admin xem danh sách moderator

- Method: `GET`
- Path: `/api/v1/admin/moderators`
- Operation ID: `admin_list_moderators`
- Authentication: Bearer JWT, role `admin`
- Path/query/body: Không có.
- Response: HTTP `200`, mảng user summary có role `moderator` hoặc `admin`.
- Lỗi: `401` hoặc `403`.
- Trạng thái xác minh: **Đã test** — Admin Management Newman.

```bash
curl http://127.0.0.1:8000/api/v1/admin/moderators ^
  -H "Authorization: Bearer <admin_token>"
```

### 3.19 Admin cấp hoặc thu hồi role

- Method: `PATCH`
- Path: `/api/v1/admin/users/{user_id}/role`
- Operation ID: `admin_update_user_role`
- Authentication: Bearer JWT, role `admin`
- Path `user_id`: UUID, bắt buộc.
- Content-Type: `application/json`
- Body: `{"role":"user"}`, `{"role":"moderator"}` hoặc `{"role":"admin"}`.
- Response: HTTP `200`, user detail sau cập nhật.
- Lỗi: `400` nếu admin tự thu hồi quyền admin; `401`, `403`, `404`, `422` theo
  auth, quyền, ID và enum.
- Trạng thái xác minh: **Đã test** — Admin Management Newman đã cấp role
  `moderator`.
- SRS còn thiếu: `Senior Moderator`, audit log, notification, session revoke
  và unassign công việc locked chưa được code.

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/admin/users/<user_id>/role ^
  -H "Authorization: Bearer <admin_token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"role\":\"moderator\"}"
```

### 3.20 Endpoint triển khai mới (phiên đăng nhập, nhãn, appeal, admin)

Nhóm endpoint dưới đây từng là placeholder và nay **đã triển khai đầy đủ**;
không còn route nào trả `501`. Quy tắc chung: thiếu token trả `401`, sai vai
trò trả `403`, sai kiểu UUID/enum trả `422`.

| # | Method | Path | Auth | Chức năng (SRS) |
|---:|---|---|---|---|
| 1 | POST | `/api/v1/auth/logout` | JWT | Đăng xuất / revoke token (UC001–UC002) |
| 2 | POST | `/api/v1/auth/refresh` | Không | Làm mới access token (UC002) |
| 3 | POST | `/api/v1/auth/password/forgot` | Không | Yêu cầu đặt lại mật khẩu (UC002) |
| 4 | POST | `/api/v1/auth/password/reset` | Không | Đặt lại mật khẩu (UC002) |
| 5 | PATCH | `/api/v1/profile` | JWT | Cập nhật hồ sơ cá nhân (UC003) |
| 6 | GET | `/api/v1/videos/{video_id}/stream` | JWT | Streaming/phát video (UC004) |
| 7 | GET | `/api/v1/videos/search` | JWT | Lọc và tìm video theo nhãn (UC009) |
| 8 | POST | `/api/v1/videos/{video_id}/labels/confirm` | JWT | Xác nhận/chỉnh sửa nhãn (UC007) |
| 9 | PATCH | `/api/v1/videos/{video_id}/labels` | JWT mod/admin | Chỉnh sửa nhãn khi kiểm duyệt (UC015) |
| 10 | POST | `/api/v1/videos/{video_id}/appeals` | JWT | Gửi yêu cầu xem xét lại (UC011) |
| 11 | GET | `/api/v1/moderation/appeals` | JWT mod/admin | Danh sách appeal (UC017) |
| 12 | POST | `/api/v1/moderation/appeals/{appeal_id}/decision` | JWT mod/admin | Xử lý appeal (UC017) |
| 13 | PATCH | `/api/v1/admin/videos/{video_id}/status` | JWT admin | Quản lý video (2.2.12) |
| 14 | GET | `/api/v1/admin/labels` | JWT admin | Liệt kê nhãn nội dung (2.2.13) |
| 15 | POST | `/api/v1/admin/labels` | JWT admin | Tạo nhãn mới (2.2.13) |
| 16 | PATCH | `/api/v1/admin/labels/{label_id}` | JWT admin | Cập nhật/vô hiệu hóa nhãn (2.2.13) |
| 17 | GET | `/api/v1/admin/moderators/{moderator_id}/stats` | JWT admin | Thống kê hiệu suất Moderator (UC019) |
| 18 | GET | `/api/v1/admin/stats` | JWT admin | Dashboard thống kê hệ thống (UC020) |

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/profile ^
  -H "Authorization: Bearer <access_token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"display_name\":\"Tên mới\"}"
```

**Hợp đồng tóm tắt của nhóm endpoint mới**

| Endpoint | Body / query | Response thành công | Lỗi điển hình |
|---|---|---|---|
| `POST /auth/logout` | `{refresh_token?}` | `204` — thu hồi `jti` của token hiện tại (và refresh token nếu gửi kèm) | `401` |
| `POST /auth/refresh` | `{refresh_token}` | `200` `{access_token, refresh_token}` — refresh token xoay vòng | `401` khi token đã dùng, bị thu hồi hoặc hết hạn |
| `POST /auth/password/forgot` | `{email}` | `202` `{detail, reset_token}` — `reset_token` chỉ trả về khi `environment != production` | `422` email sai định dạng |
| `POST /auth/password/reset` | `{token, new_password}` | `204` — đổi mật khẩu và thu hồi toàn bộ refresh token | `400` token sai, hết hạn hoặc đã dùng |
| `PATCH /profile` | `{display_name}` hoặc `{current_password, new_password}` | `200` user | `400` sai mật khẩu hiện tại; `422` thiếu trường |
| `GET /videos/{video_id}/stream` | header `Range` (VD `bytes=0-3`) | `200`/`206`, `content-type: video/mp4`, `accept-ranges: bytes` | `404` không có quyền, video chưa đăng hoặc file mất |
| `GET /videos/search` | `label`, `exclude_label`, `q`, `limit` (1–100, mặc định 50) | `200` danh sách video kèm `labels` và `owner_display_name` | `401`; `422` limit ngoài khoảng |
| `POST /videos/{video_id}/labels/confirm` | `{labels:[{name, confidence}]}` | `200` danh sách nhãn sau ghi (multi-label) | `400` nhãn chưa tồn tại/trùng/vô hiệu; `404` không phải chủ video |
| `PATCH /videos/{video_id}/labels` | như trên | `200` — thay thế toàn bộ nhãn của video | `403` với user thường |
| `POST /videos/{video_id}/appeals` | `{reason}` (3–1000 ký tự) | `201` appeal `open` kèm `user_display_name` | `400` video chưa bị từ chối; `409` đã có appeal đang mở; `404` không phải chủ |
| `GET /moderation/appeals` | `status=open\|approved\|rejected` (mặc định `open`) | `200` danh sách kèm tên người khiếu nại | `403` |
| `POST /moderation/appeals/{appeal_id}/decision` | `{action: approve\|reject, reason?}` | `204` — `approve` đăng lại video, `reject` giữ nguyên | `409` đã xử lý; `404` sai id |
| `PATCH /admin/videos/{video_id}/status` | `{status: pending_review\|published\|rejected\|deleted, reason?}` | `200` video (`deleted` = soft delete) | `404`; `422` sai enum (không nhận `processing`) |
| `GET /admin/labels` | — | `200` danh sách kèm `video_count` | `403` |
| `POST /admin/labels` | `{name}` | `201` nhãn mới | `409` trùng tên (không phân biệt hoa thường) |
| `PATCH /admin/labels/{label_id}` | `{name?}`, `{is_active?}` | `200` nhãn sau cập nhật | `409` trùng tên; `422` thiếu trường; `404` |
| `GET /admin/moderators/{moderator_id}/stats` | — | `200` `{videos_reviewed, reviews_approved, reviews_rejected, appeals_handled}` | `400` người dùng không phải moderator/admin; `404` |
| `GET /admin/stats?days=1..365` | — | `200` dashboard UC020: video theo trạng thái, phân bố nhãn (kèm `ratio`), report/appeal/job theo trạng thái, khối lượng Moderator | `422` `days` ngoài khoảng; `403` |

- Trạng thái xác minh: **Đã test** — 20 test pytest mới
  (`test_auth_session.py`, `test_video_stream_search.py`,
  `test_labels_appeals_admin.py`) và smoke test runtime đầy đủ trên Neon
  (tạo nhãn → xác nhận nhãn → search → reject → appeal → approve → stats).

## 4. Luồng gọi API thực tế

### 4.1 Tạo user và đọc profile

1. `POST /api/v1/auth/register` với email/display name/password.
2. `POST /api/v1/auth/login` với cùng email/password.
3. Lưu `access_token` trong biến Postman `access_token`.
4. Gửi `GET /api/v1/profile` với
   `Authorization: Bearer {{access_token}}`.

### 4.2 Upload và đọc AI result

1. Login để lấy `access_token`.
2. `POST /api/v1/videos?caption=Demo`, multipart field `file`.
3. Lưu `id` trong response thành `video_id`.
4. Gọi `GET /api/v1/videos/{video_id}/ai`.
5. Nếu NSFW-Detection chạy được, transcript chứa phán quyết `ADULT`/`NORMAL` và
   label tương ứng (`Adult` đưa video vào `pending_review`, `Safe` đăng công khai).
   Nếu môi trường AI chưa sẵn sàng, transcript ghi rõ lý do và kết quả là mock:
   `job_status: "succeeded"`, label `Safe` 0.95. Không coi đây là kết quả AI
   production.

### 4.3 Report và moderation

1. User login.
2. Upload video và lấy `video_id`, hoặc dùng ID video hiện có.
3. Gửi `POST /api/v1/videos/{video_id}/reports`.
4. Moderator/admin login và gửi `GET /api/v1/moderation/queue` hoặc
   `GET /api/v1/moderation/reports`.
5. Lấy `report_id` từ danh sách report mở.
6. Gửi `POST /api/v1/moderation/reports/{report_id}/decision`.
7. Không gửi lại report đã xử lý; implementation trả `404`.

## 5. Bảng tổng hợp endpoint

| STT | Method | Path | Module | Auth | Trạng thái kiểm thử |
|---:|---|---|---|---|---|
| 1 | GET | `/health` | System | Không | Đã test |
| 2 | POST | `/api/v1/auth/register` | Auth | Không | Đã test |
| 3 | POST | `/api/v1/auth/login` | Auth | Không | Đã test |
| 4 | GET | `/api/v1/profile` | User Profile | JWT | Đã test |
| 5 | POST | `/api/v1/videos` | Video Upload | JWT | Đã test |
| 6 | GET | `/api/v1/videos` | Video Management | JWT | Đã test |
| 7 | GET | `/api/v1/feed` | Video Management | Không | Đã test |
| 8 | GET | `/api/v1/videos/{video_id}/ai` | AI Analysis | JWT + owner/mod/admin | Đã test |
| 9 | DELETE | `/api/v1/videos/{video_id}` | Video Management | JWT + owner | Đã test |
| 10 | POST | `/api/v1/videos/{video_id}/reports` | Content Report | JWT | Đã test |
| 11 | GET | `/api/v1/moderation/queue` | Moderation | JWT + mod/admin | Đã test |
| 12 | POST | `/api/v1/moderation/videos/{video_id}/decision` | Moderation | JWT + mod/admin | Code/OpenAPI |
| 13 | GET | `/api/v1/moderation/reports` | Moderation | JWT + mod/admin | Đã test |
| 14 | POST | `/api/v1/moderation/reports/{report_id}/decision` | Moderation | JWT + mod/admin | Đã test |
| 15 | GET | `/api/v1/admin/users` | Admin Management | JWT + admin | Đã test |
| 16 | GET | `/api/v1/admin/users/{user_id}` | Admin Management | JWT + admin | Đã test |
| 17 | PATCH | `/api/v1/admin/users/{user_id}/status` | Admin Management | JWT + admin | Đã test |
| 18 | GET | `/api/v1/admin/moderators` | Admin Management | JWT + admin | Đã test |
| 19 | PATCH | `/api/v1/admin/users/{user_id}/role` | Admin Management | JWT + admin | Đã test |
| 20 | POST | `/api/v1/auth/logout` | Auth | JWT | Đã test |
| 21 | POST | `/api/v1/auth/refresh` | Auth | Không | Đã test |
| 22 | POST | `/api/v1/auth/password/forgot` | Auth | Không | Đã test |
| 23 | POST | `/api/v1/auth/password/reset` | Auth | Không | Đã test |
| 24 | PATCH | `/api/v1/profile` | User Profile | JWT | Đã test |
| 25 | GET | `/api/v1/videos/{video_id}/stream` | Video Playback | JWT | Đã test |
| 26 | GET | `/api/v1/videos/search` | Video Search | JWT | Đã test |
| 27 | POST | `/api/v1/videos/{video_id}/labels/confirm` | Labels | JWT + owner | Đã test |
| 28 | PATCH | `/api/v1/videos/{video_id}/labels` | Labels | JWT + mod/admin | Đã test |
| 29 | POST | `/api/v1/videos/{video_id}/appeals` | Appeal | JWT + owner | Đã test |
| 30 | GET | `/api/v1/moderation/appeals` | Appeal | JWT + mod/admin | Đã test |
| 31 | POST | `/api/v1/moderation/appeals/{appeal_id}/decision` | Appeal | JWT + mod/admin | Đã test |
| 32 | PATCH | `/api/v1/admin/videos/{video_id}/status` | Admin Management | JWT + admin | Đã test |
| 33 | GET | `/api/v1/admin/labels` | Label Management | JWT + admin | Đã test |
| 34 | POST | `/api/v1/admin/labels` | Label Management | JWT + admin | Đã test |
| 35 | PATCH | `/api/v1/admin/labels/{label_id}` | Label Management | JWT + admin | Đã test |
| 36 | GET | `/api/v1/admin/moderators/{moderator_id}/stats` | Admin Analytics | JWT + admin | Đã test |
| 37 | GET | `/api/v1/admin/stats` | Admin Analytics | JWT + admin | Đã test |

## 6. Đối chiếu và giới hạn

- OpenAPI runtime trả 37 operation hoạt động; không còn endpoint `501` nào.
- Tất cả route vẫn được đăng ký trực tiếp trong `app/main.py`; chưa dùng
  APIRouter cho từng module.
- `GET /api/v1/videos/{video_id}/stream` phục vụ file local qua `FileResponse`
  (hỗ trợ HTTP Range); `storage_path` không được trả ra trong `VideoResponse`.
- Logout thu hồi `jti` của access token hiện tại; refresh token xoay vòng và bị
  thu hồi khi dùng lại hoặc khi đổi mật khẩu. Chưa có kênh gửi mail nên
  `reset_token` chỉ được trả về ngoài môi trường `production`.
- Admin Management có list/detail/status/role user, quản lý nhãn, quản lý trạng
  thái video và 2 endpoint thống kê (UC019/UC020).
- Feed/report/queue chưa có pagination; chỉ `/videos/search` nhận `limit`.
- AI result do pipeline NSFW-Detection (`app.ai.nsfw`) sinh ra khi môi trường
  AI đã cài; nếu chưa, job ghi rõ lý do trong transcript và dùng kết quả mock.
  Speech-to-text và các detector violence/sound/text vẫn là placeholder.
- Endpoint quyết định video moderation đã đối chiếu source/OpenAPI nhưng chưa có
  request Newman riêng; vì vậy được đánh dấu `Code/OpenAPI`, không đánh dấu
  `Đã test`.
- Các response ví dụ UUID/thời gian là placeholder an toàn, trừ các giá trị
  mock AI và status đã được xác minh trong test local.
- Không đưa password, JWT thật, secret, API key, connection string hoặc dữ liệu
  cá nhân vào tài liệu.
