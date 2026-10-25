# PBL6 AI Short Video Moderation

Backend MVP cho nền tảng video ngắn có AI gợi ý nhãn và quy trình kiểm duyệt.

## Phạm vi MVP

- FastAPI, PostgreSQL, SQLAlchemy 2.x và Alembic.
- Đăng ký, đăng nhập JWT và phân quyền `User`, `Moderator`, `Admin`.
- Upload video `.mp4` tối đa 50MB vào local storage.
- Mock AI/STT chạy bằng FastAPI `BackgroundTasks`.
- Nhãn đa trị, confidence level `LOW/MEDIUM/HIGH`.
- Feed chỉ hiển thị video đã publish.
- Report video, hàng đợi moderation cơ bản và soft delete.

Appeal, email notification, dashboard analytics, Celery/Redis và AI/STT thật chưa nằm trong MVP.

### Kiểm thử upload bằng video thật (local only)

Nếu workspace có thư mục `TestDataset`, pytest sẽ tự chọn file `.mp4` đầu tiên
trong thư mục này. Backend kiểm tra MP4 magic bytes, brand và codec video được
hỗ trợ trước khi lưu vào `UPLOAD_DIR` local. Hiện tại adapter AI chỉ là
`run_mock_analysis`; không có Cloud Storage hoặc API AI bên ngoài.

Chạy kiểm thử:

```powershell
cd E:\PBL6\backend
.\.venv\Scripts\python.exe -m pytest -q
cd E:\PBL6
newman run .\local-tests\postman\video-upload_v1.0.0.postman_collection.json `
  --env-var "base_url=http://127.0.0.1:8000"
```

Video trong `TestDataset` và các fixture/log Postman local không được commit.

## Thiết lập PostgreSQL trên Windows 10/11

Phần này mô tả quy trình từ máy chưa có PostgreSQL đến khi Backend truy vấn
được database. Các lệnh dùng PowerShell và không yêu cầu gửi mật khẩu thật
trong cuộc trò chuyện.

### 1. Kiểm tra PostgreSQL

Mở PowerShell mới và kiểm tra client, service, host và port:

```powershell
psql --version
Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
Test-NetConnection -ComputerName localhost -Port 5432
```

Nếu `psql` không được nhận diện, PostgreSQL chưa có trong `PATH`. Có thể gọi
trực tiếp bằng đường dẫn mặc định (điều chỉnh version nếu cần):

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" --version
```

Nếu chưa cài, tải PostgreSQL từ trang chính thức:
<https://www.postgresql.org/download/windows/>. Trong trình cài đặt:

1. Giữ port mặc định `5432` nếu port này chưa bị sử dụng.
2. Đặt mật khẩu riêng cho role quản trị `postgres`; không dùng mật khẩu đó
   trong source code hoặc tài khoản ứng dụng.
3. Có thể cài pgAdmin và Command Line Tools.

Sau khi cài, kiểm tra service:

```powershell
Get-Service -Name "postgresql*" | Format-Table Name,Status,StartType
Start-Service -Name "postgresql-x64-16" # thay tên bằng kết quả thực tế
```

Nếu service đã chạy, không cần gọi `Start-Service`. Host mặc định là
`localhost`, port là `5432`, còn database/role sẽ được tạo ở bước tiếp theo.
Có thể dùng `psql` hoặc pgAdmin để thực hiện các câu lệnh SQL.

### 2. Tạo database và role ứng dụng

Đăng nhập bằng role quản trị cục bộ. Thay `postgres` bằng role quản trị của
bạn nếu đã chọn tên khác:

```powershell
psql -h localhost -p 5432 -U postgres -d postgres
```

Trong cửa sổ `psql`, thay các giá trị mẫu bằng mật khẩu riêng của bạn. Không
đưa mật khẩu thật vào README, script hoặc Git:

```sql
CREATE ROLE pbl6_app WITH LOGIN PASSWORD 'CHANGE_ME_TO_A_PRIVATE_PASSWORD';
CREATE DATABASE pbl6 OWNER pbl6_app;
\c pbl6
GRANT CONNECT ON DATABASE pbl6 TO pbl6_app;
GRANT USAGE, CREATE ON SCHEMA public TO pbl6_app;
\du pbl6_app
\l pbl6
\q
```

Role `pbl6_app` chỉ phục vụ Backend; không dùng role superuser `postgres` cho
ứng dụng trong môi trường thông thường. Nếu database hoặc role đã tồn tại,
không chạy lại lệnh tạo một cách mù quáng; kiểm tra trước:

```powershell
psql -h localhost -p 5432 -U postgres -d postgres -c "\du"
psql -h localhost -p 5432 -U postgres -d postgres -c "\l"
```

Kiểm tra quyền bằng tài khoản ứng dụng:

```powershell
psql -h localhost -p 5432 -U pbl6_app -d pbl6 -c "SELECT current_user, current_database(), version();"
```

Backend cũng có thể kiểm tra kết nối mà không in mật khẩu:

```powershell
cd E:\PBL6\backend
.\.venv\Scripts\Activate.ps1
python -m scripts.check_db
```

### 3. Cấu hình `.env`

Từ thư mục `E:\PBL6\backend`:

```powershell
Copy-Item .env.example .env
notepad .env
```

Sửa `DATABASE_URL` thành:

```dotenv
DATABASE_URL=postgresql+psycopg://pbl6_app:YOUR_PASSWORD@localhost:5432/pbl6
```

Ý nghĩa các thành phần:

- `postgresql+psycopg`: SQLAlchemy dùng dialect PostgreSQL và driver `psycopg`.
- `pbl6_app`: role ứng dụng.
- `YOUR_PASSWORD`: mật khẩu role ứng dụng.
- `localhost:5432`: host và port PostgreSQL.
- `pbl6`: tên database.

Nếu mật khẩu có ký tự đặc biệt như `@`, `:`, `/`, `#` hoặc khoảng trắng,
hãy URL-encode phần mật khẩu trước khi đặt vào URL. Ví dụ, `pa@ss#word`
thành `pa%40ss%23word`. Không ghi mật khẩu thật vào commit hoặc gửi qua chat.

`SECRET_KEY` trong `.env` cũng phải được thay bằng giá trị dài, ngẫu nhiên ở
môi trường thực tế. File `.env` đã được bỏ qua bởi `.gitignore`.

### 4. Cài dependency PostgreSQL

Dự án dùng duy nhất driver `psycopg` (không dùng `psycopg2`). Từ thư mục
Backend:

```powershell
cd E:\PBL6\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -c "import psycopg; print(psycopg.__version__)"
```

Dependency tương ứng là `psycopg[binary]` trong
[requirements.txt](backend/requirements.txt). Không cần cài thêm driver
PostgreSQL khác.

### 5. Chạy và kiểm tra Alembic migration

Đảm bảo đang ở `E:\PBL6\backend`, virtual environment đã kích hoạt và `.env`
đang trỏ tới đúng database:

```powershell
alembic current
alembic upgrade head
alembic current
psql -h localhost -p 5432 -U pbl6_app -d pbl6 -c "\dt"
alembic history
```

Migration đầu tiên tạo các bảng `users`, `videos`, `labels`, `video_labels`,
`ai_jobs`, `moderation_reviews` và `reports`. `alembic current` sau khi nâng
cấp phải hiển thị revision `0001_initial`.

Không `DROP DATABASE`, xóa volume hoặc reset dữ liệu để sửa lỗi migration.
Nếu database có dữ liệu, hãy kiểm tra trạng thái và tạo migration mới:

```powershell
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

### 6. Kiểm tra end-to-end và chạy Backend

Thực hiện theo thứ tự:

```powershell
Get-Service -Name "postgresql*" | Where-Object Status -eq "Running"
Test-NetConnection localhost -Port 5432
psql -h localhost -p 5432 -U pbl6_app -d pbl6 -c "SELECT 1;"
alembic current
uvicorn app.main:app --reload
```

Trong PowerShell khác:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Kết quả mong đợi của health endpoint là `status: ok`. Sau đó mở Swagger tại
`http://127.0.0.1:8000/docs` và thử đăng ký tài khoản. API này sẽ truy vấn
PostgreSQL qua `DATABASE_URL`.

Nếu local đang dùng role `postgres` để khởi động MVP, hãy chuyển sang role
`pbl6_app` trước khi triển khai hoặc chia sẻ môi trường. Role `postgres` là
superuser và chỉ nên được dùng tạm thời cho local bootstrap.

### 7. PostgreSQL bằng Docker Compose (tùy chọn)

Nếu không muốn cài PostgreSQL native, repository có
[docker-compose.yml](docker-compose.yml):

```powershell
cd E:\PBL6
$env:POSTGRES_ADMIN_PASSWORD = "CHANGE_ME_ADMIN_PASSWORD"
$env:POSTGRES_APP_PASSWORD = "CHANGE_ME_APP_PASSWORD"
docker compose up -d postgres
docker compose ps
docker compose logs postgres
```

Compose MVP tạo database `pbl6`, role quản trị bootstrap `postgres`, role ứng
dụng `pbl6_app` và port `5432`. Hai mật khẩu chỉ được truyền qua biến môi
trường PowerShell; không đặt chúng trong source code. Script khởi tạo
[01-create-app-role.sh](docker/postgres/01-create-app-role.sh) tạo role ứng
dụng và chuyển owner database sang role này. Đây chỉ là cấu hình local tiện
dụng; không dùng các mật khẩu local ở production.

Các script trong `/docker-entrypoint-initdb.d` chỉ chạy khi PostgreSQL volume
được khởi tạo lần đầu. Nếu container đã có volume, role/database hiện tại
không bị ghi đè; hãy kiểm tra bằng `psql` và tạo role thủ công theo bước 2
nếu cần. Không xóa volume để ép chạy lại script.

Dừng container nhưng giữ dữ liệu:

```powershell
docker compose stop postgres
docker compose start postgres
```

Không chạy `docker compose down -v`: tùy chọn `-v` xóa volume và dữ liệu
PostgreSQL. `docker compose down` không có `-v` chỉ dừng/xóa container và
giữ volume.

### 8. Xử lý lỗi thường gặp

| Lỗi | Kiểm tra | Nguyên nhân/cách xử lý an toàn |
|---|---|---|
| `connection refused` | `Test-NetConnection localhost -Port 5432` | Service/container chưa chạy, port sai hoặc PostgreSQL không lắng nghe trên port đó. Khởi động service/container và kiểm tra log. |
| Sai host/port | `psql -h localhost -p 5432 ...` | Đối chiếu host/port với `DATABASE_URL`; không đổi database hoặc xóa volume để sửa lỗi này. |
| `password authentication failed` | Thử `psql` bằng đúng role | Kiểm tra username, mật khẩu và URL-encoding ký tự đặc biệt. Đặt lại mật khẩu bằng tài khoản quản trị chỉ khi cần. |
| `database does not exist` | `psql ... -d postgres -c "\l"` | Tạo `pbl6` theo bước 2 hoặc sửa đúng tên database trong `.env`. |
| `permission denied` | `\du`, `\dn+ public` bằng admin | Cấp `CONNECT`, `USAGE`, `CREATE` cho `pbl6_app`; không cấp superuser chỉ để né lỗi. |
| Thiếu driver PostgreSQL | `python -c "import psycopg"` | Kích hoạt đúng `.venv`, rồi chạy `python -m pip install -r requirements.txt`. |
| Sai `DATABASE_URL` | Kiểm tra `.env` và chạy `python -c "from app.config import get_settings; from sqlalchemy.engine import make_url; u=make_url(get_settings().database_url); print(u.drivername, u.host, u.port, u.database, u.username)"` | Sửa scheme `postgresql+psycopg`, role, mật khẩu đã encode, host, port và database. Không in URL có mật khẩu trong log chia sẻ. |
| Migration lỗi | `alembic current`, xem lỗi cụ thể | Xác minh quyền/schema và URL trước; không drop database. Sửa migration chưa áp dụng hoặc tạo migration mới. |
| Service chưa khởi động | `Get-Service -Name "postgresql*"` | Dùng đúng tên service thực tế từ kết quả, hoặc xem log Docker bằng `docker compose logs postgres`. |

### 9. Development và production

- Không dùng credentials production trên máy phát triển.
- Không commit `.env`, secret, video upload hoặc database dump.
- Không dùng `postgres` superuser làm tài khoản ứng dụng thông thường.
- Không xóa volume/database khi chỉ gặp lỗi kết nối.
- Native PostgreSQL và Docker Compose là hai lựa chọn thay thế; chỉ cần dùng
  một lựa chọn tại một thời điểm để tránh tranh chấp port `5432`.
- Môi trường production cần secret manager, TLS, backup/restore đã kiểm thử,
  giới hạn network và role database tối thiểu.

## Test

```powershell
cd E:\PBL6\backend
pytest -q
```

Test API dùng SQLite tạm thời để không yêu cầu PostgreSQL đang chạy; môi trường chạy thật dùng PostgreSQL qua `DATABASE_URL`.

## Migration

```powershell
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

Không reset hoặc drop database để áp dụng migration.

## API MVP

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/profile`
- `POST /api/v1/videos`
- `GET /api/v1/videos`
- `GET /api/v1/feed`
- `GET /api/v1/videos/{video_id}/ai`
- `DELETE /api/v1/videos/{video_id}`
- `POST /api/v1/videos/{video_id}/reports`
- `GET /api/v1/moderation/queue`
- `POST /api/v1/moderation/videos/{video_id}/decision`
- `GET /api/v1/moderation/reports`
- `POST /api/v1/moderation/reports/{report_id}/decision`

## Biến môi trường

Xem `backend/.env.example`. Không commit `.env`, secret thật, video upload hoặc database dump.
