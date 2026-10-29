# PBL6 User and Operator Guide

## 1. What this system is

PBL6 is a FastAPI backend for authenticated short-video upload and moderation.
It stores uploaded MP4 files on the local filesystem, stores metadata and
analysis results in PostgreSQL, and runs an Adult-content pipeline through a
background task.

Current roles are:

- `user`: upload and manage owned videos, inspect AI results, report videos,
  confirm labels, and submit appeals for rejected owned videos.
- `moderator`: review pending videos/reports/appeals and edit labels.
- `admin`: moderator permissions plus user, label, video-status, and statistics
  management.

The frontend is a Vite/React application under `frontend/`. It is runnable
independently, but not every SRS workflow is implemented in the UI yet.

## 2. Requirements

- Windows PowerShell is supported by the commands below.
- Python 3.12 was used for the verified environment.
- Backend dependencies: root `pyproject.toml` and `uv.lock`, managed by `uv`.
- Frontend dependencies: `frontend\package.json` and
  `frontend\package-lock.json`, managed by npm.
- Real AI dependencies: `backend\NSFW-Detection\src\pyproject.toml` and its
  `uv.lock`.
- PostgreSQL Neon credentials supplied locally through `backend\.env`.
- Real model files under `backend\NSFW-Detection\src\models\`.
- A local MP4 such as `local\TestDataset-v2\Travel_4.mp4`.
- Newman for API collections.

The real AI run was verified with TensorFlow 2.20.0, Keras 3.13.2, PyTorch
2.6.0 CPU, OpenCV 4.14.0, and NumPy 2.0.2.

## 3. First-time setup

```powershell
Set-Location E:\PBL6
uv venv
uv sync
Set-Location frontend
npm install
Set-Location ..
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env` locally. Required names are:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
SECRET_KEY=replace-with-a-long-random-secret
UPLOAD_DIR=storage/uploads
MAX_UPLOAD_SIZE_BYTES=52428800
AI_ANALYSIS_MODE=required
NSFW_PIPELINE_DIR=NSFW-Detection/src
NSFW_PYTHON=
NSFW_TIMEOUT_SECONDS=600
```

Use URL encoding for reserved characters in a PostgreSQL password. Never put
the real value in source, Postman collections, reports, or chat.

The model files are local-only and ignored by Git. Place the actual model
artifacts at:

```text
backend\NSFW-Detection\src\models\mobilenetv3_small_adult_normal.keras
backend\NSFW-Detection\src\models\resnet50_adult_normal_fcn_layer4_classifier.pth
```

## 4. Database and startup

Verify the database without printing the connection string:

```powershell
Set-Location E:\PBL6\backend
uv run python scripts\check_db.py
uv run alembic current
uv run alembic upgrade head
```

`upgrade head` is an additive migration operation in this repository, but
inspect the current revision before applying any future migration. Do not drop,
reset, truncate, or delete Neon data to solve a migration problem.

Start the backend:

```powershell
$env:AI_ANALYSIS_MODE="required"
$env:PROJ6_DEVICE="cpu"
$env:PYTHONUTF8="1"
Set-Location E:\PBL6
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Start-Process http://127.0.0.1:8000/docs
```

The server exposes `/docs`, `/redoc`, and `/openapi.json`.

## 5. Normal user workflow

1. Register with `POST /api/v1/auth/register`.
2. Login with `POST /api/v1/auth/login`.
3. Send `Authorization: Bearer <access_token>`.
4. Upload an MP4 using `POST /api/v1/videos?caption=...` and multipart field
   `file`.
5. Poll `GET /api/v1/videos/{video_id}/ai` until the job is `succeeded` or
   `failed`.
6. Use `GET /api/v1/videos`, `/feed`, `/stream`, and `/search` as permitted.
7. Report a published video with `POST /api/v1/videos/{video_id}/reports`.
8. Use the appeal endpoint only after an owned video is `rejected`.

With `AI_ANALYSIS_MODE=required`, missing model/runtime or inference failure
causes a failed job rather than a mock publication. `auto` permits the
development fallback; `off` always uses mock analysis and is not evidence of
real AI.

## 6. Operational limitations

- Only the Adult detector is real. Violence, sound, and text/STT detectors are
  placeholders.
- The verified sample produced `NORMAL`, `Safe`, confidence `0.0014`, level
  `LOW`, and `published`. The current code publishes every result without
  detections; it does not route low-confidence Safe results to review.
- There is no email provider for password reset; outside production the reset
  token is returned for local testing.
- Upload storage is local, not object storage.
- Moderation has no claim/lock workflow or complete audit log.
- The frontend is runnable from `frontend/`, although it does not yet cover
  every SRS workflow.

## 7. Data safety

This workspace uses Neon for API testing. Test accounts, videos, jobs, labels,
and reports created by Newman may remain there. Do not clean them up unless
ownership and exact deletion scope are confirmed and approved.
