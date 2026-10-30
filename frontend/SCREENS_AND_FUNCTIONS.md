# Mô tả các màn hình & chức năng (Frontend)

Tài liệu này mô tả các trang (screens) hiện có trong frontend, chức năng tương ứng, route, quyền truy cập và các component/features liên quan.

## Tổng quan routes (từ `src/app/App.jsx`)

| Route | Component | Layout | Quyền truy cập | Mô tả |
|---|---|---|---|---|
| `/` | `FeedPage` | `MainLayout` | Công khai (ai cũng xem được) | Trang feed video ngắn (hiển thị danh sách video đã được phân tích/published theo feed). |
| `/upload` | `UploadPage` | `MainLayout` | `RequireAuth` (cần đăng nhập) | Tải video lên, nhập caption, theo dõi tiến trình upload và kết quả phân tích AI. |
| `/profile` | `ProfilePage` | `MainLayout` | `RequireAuth` (cần đăng nhập) | Quản lý video cá nhân: danh sách video của user, xem kết quả AI, xóa video. |
| `/moderation` | `ModerationPage` | `MainLayout` | `RequireRole` (`moderator`, `admin`) | Hàng đợi kiểm duyệt: duyệt/từ chối video chờ duyệt và xử lý báo cáo người dùng. |
| `/login` | `LoginPage` | Không có (auth-shell) | Công khai | Đăng nhập tài khoản. |
| `/register` | `RegisterPage` | Không có (auth-shell) | Công khai | Đăng ký tài khoản mới. |
| `*` | `Navigate to="/"` | - | Công khai | Chuyển hướng về trang chủ nếu route không tồn tại. |

## Chi tiết các màn hình

### 1. FeedPage (`src/pages/FeedPage.jsx`)
- **Chức năng chính:** Hiển thị feed video.
- **Thành phần sử dụng:** `VideoFeed` (`src/features/videos/components/VideoFeed.jsx`).
- **Chi tiết:** Trang chỉ render `VideoFeed`, toàn bộ logic hiển thị feed (lấy danh sách, phát video, tương tác...) nằm ở component `VideoFeed`.

### 2. LoginPage (`src/pages/LoginPage.jsx`)
- **Chức năng chính:** Giao diện đăng nhập.
- **Thành phần sử dụng:** `AuthCard` với `mode="login"` (`src/features/auth/components/AuthCard.jsx`).
- **Layout:** `.auth-shell` (không sử dụng `MainLayout`).
- **Chi tiết:** Chỉ render form đăng nhập, logic đăng nhập/điều hướng nằm ở `AuthCard` và `AuthContext`.

### 3. RegisterPage (`src/pages/RegisterPage.jsx`)
- **Chức năng chính:** Giao diện đăng ký tài khoản.
- **Thành phần sử dụng:** `AuthCard` với `mode="register"`.
- **Layout:** `.auth-shell`.
- **Chi tiết:** Tương tự LoginPage, xử lý đăng ký tài khoản mới.

### 4. UploadPage (`src/pages/UploadPage.jsx`)
- **Chức năng chính:** Tải video lên và theo dõi phân tích AI.
- **Quyền:** Cần đăng nhập.
- **Thành phần sử dụng:**
  - `UploadDropzone` - Chọn/kéo thả file video MP4.
  - `useVideoUpload()` hook - Quản lý trạng thái upload, tiến trình, kết quả upload.
  - `AiResultPanel` - Hiển kết quả phân tích AI sau khi upload thành công.
  - `Icon`, `ErrorNote` - Component dùng chung.
- **Chức năng cụ thể:**
  - **Chọn file:** Kéo thả hoặc chọn file MP4 (giới hạn hiển thị "MP4 · tối đa 50 MB").
  - **Nhập caption:** Ô nhập mô tả không bắt buộc (tối đa 500 ký tự).
  - **Upload:** Gửi file + caption lên backend, theo dõi % tiến trình upload.
  - **Sau khi upload thành công:** Hiển thị 2 nút "Tải video khác" (reset form) và "Xem ở feed" (đến `/`).
  - **Thông tin hỗ trợ:** Panel bên phải mô t right các thông tin về quy trình kiểm duyệt tự động (kiểm tra magic bytes/codec, chạy job AI nền, poll kết quả, video xuất hiện ở feed sau khi phân tích xong, báo cáo có thể đưa vào hàng đợi kiểm duyệt).
  - **Kết quả AI:** Nếu upload thành công (`uploadedVideo` tồn tại), hiển thị `AiResultPanel` để xem kết quả phân tích AI của video vừa upload.

### 5. ProfilePage (`src/pages/ProfilePage.jsx`)
- **Chức năng chính:** Trang cá nhân - quản lý video của người dùng hiện tại.
- **Quyền:** Cần đăng nhập.
- **Thành phần sử dụng:**
  - `useAuth()` - Lấy thông tin user hiện tại.
  - `fetchMyVideos()`, `deleteVideo()`, `streamUrl()` từ `features/videos/api/videosApi`.
  - `AiResultPanel` - Xem kết quả phân tích AI của video được chọn.
  - `StatusBadge`, `Spinner`, `EmptyState`, `ErrorNote` - Components dùng chung.
- **Chức năng cụ thể:**
  - **Header profile:** Hiển thị avatar (2 chữ cái đầu tên), tên hiển thị, email, vai trò, thống kê (tổng số video, số video "Đã phát"/`published`, số video "Chờ duyệt"/`pending_review`).
  - **Danh sách video:** Danh sách các video đã upload của user, mỗi item hiển thị thumbnail (video muted/preload metadata), tên/caption, ngày tạo, dung lượng, trạng thái (`StatusBadge` với label theo `VIDEO_STATUS_LABEL`).
  - **Chọn video:** Click vào video trong danh sách để xem kết quả phân tích AI (`AiResultPanel`) bên phía phải.
  - **Xóa video:** Nút xóa với icon thùng rác, có trạng thái `busyId` khi đang xóa.
  - **Trạng thái trống:** Nếu chưa có video nào, hiển
  - **Trạng thái trống:** Nếu chưa có video nào, hiển thị `EmptyState` với nút "Tải video đầu tiên" dẫn đến `/upload`.

### 6. ModerationPage (`src/pages/ModerationPage.jsx`)
- **Chức năng chính:** Hàng đợi kiểm duyệt dành cho `moderator` và `admin`.
- **Quyền:** `RequireRole` với roles `['moderator', 'admin']`.
- **Thành phần sử dụng:**
  - `useModerationList()` hook - Quản lý danh sách (queue/reports).
  - `fetchQueue()`, `fetchReports()`, `decideVideo()`, `decideReport()` từ `features/moderation/api/moderationApi`.
  - `streamUrl()` từ `features/videos/api/videosApi`.
  - `Icon`, `Spinner, EmptyState, ErrorNote` - Components dùng chung.
- **Chức năng cụ thể:**
  - **Tabs:** Chuyển đổi giữa 2 tab: "Hàng đợi video" (`queue`) và "Báo cáo" (`reports`).
  - **Tab hàng đợi video:**
    - Danh sách các video đang chờ duyệt (`pending_review`).
    - Mỗi card hiển thị video preview (controls), caption/original_filename, owner, dung lượng, ngày tạo, badge trạng thái "Chờ duyệt".
    - **Duyệt đăng:** `approve` - Duyệt video, chuyển trạng thái thành công (có thể `published`).
    - **Từ chối:** `reject` - Từ chối video.
  - **Tab báo cáo:**
    - Danh sách báo cáo đang mở (`Report`).
    - Mỗi card hiển trường lý báo cáo ("reason"), thông tin video bị báo cáo.
    - **Xác nhận vi phạm:** `approve` - Xác nhận báo cáo, xử lý theo hành động vi phạm.
    - **Bác bỏ báo cáo:** `reject` - Bác bỏ báo cáo không đúng.
  - **Refresh tự động:** Sau khi quyết định xong, gọi `queue.refresh()` và `reports.refresh()`.
  - **Trạng thái trống:** Hiển thị `EmptyState` nếu không có gì trong tab hiện tại.

## Layout & Navigation

- **MainLayout** (`src/app/layout/MainLayout.jsx`): Layout chung cho các trang có trong routes (Feed, Upload, Profile, Moderation). Thường chứa `SideNav` và `TopBar`.
- **SideNav** (`src/app/layout/SideNav.jsx`): Điều hướng chính (Feed, Upload, Profile, Modertaion nếu có quyền).
- **TopBar** (`src/app/layout/TopBar.jsx`): Thanh trên, thông tin user/auth.
- **AuthContext** (`src/features/auth/AuthContext.jsx`): Quản lý trạng thái đăng nhập, user, token, các hàm `login`, logout, `register`, etc.
- **Guards** (`src/app/guards.jsx`): `RequireAuth` và `RequireRole` để bảo vệ route.

## Features liên quan

| Feature | Thư mục | Mô tả |
| h1::\{11 |
-|---|---|---|
| `auth` | `src/features/auth/` | Đăng nhập, đăng ký, AuthContext, AuthCard, guard logic.
| `videos` | `src/features/videos/` | Upload video, feed, AiResultPanel, API/video hooks, xử lý upload và phân tích AI.
| `moderation` | `src/features/moderation/` | Hàng đợi kiểm duyệt, xử lý báo cáo, API/mod hooks.
| `shared` | `src/shared/` | Components dùng chung (Icon, Feedback, etc., UI elements), utilities, formatters, lib.

## Ghi chú

- FE hiện đang giả định backend chạy tại 1 địa chỉ nào đó (xem các file API trong features) và sẽ không hoạt động nếu backend không kết nối được.
- `AiResultPanel` được sử dụng nhiều lần (UploadPage sau upload, ProfilePage khi chọn video) để hiển thị kết quả phân tích AI của video.
- Trang `FeedPage` chỉ là wrapper đơn giản cho `VideoFeed`, cần xem chi tiết component này để hiểu chính xác chức năng feed.
- Routes dành cho auth (`login`, `register`) không dùng `MainLayout` để tạo không gian đăng nhập riêng biệt.

**Ngày cập nhật:** Fri Oct 30 2026
