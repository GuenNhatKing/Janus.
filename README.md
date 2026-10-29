# PBL6 — AI Short Video Moderation Platform

PBL6 is a FastAPI backend for a short-video platform with JWT authentication,
local video storage, AI content analysis, user reports, and moderation
workflows.

AI analysis is integrated with the local `NSFW-Detection` pipeline (Adult
detection, TensorFlow + PyTorch) through a subprocess adapter. While the AI
environment is not installed, the job records why and falls back to the mock
result instead of failing. Violence, sound and text/STT detection are still
detector placeholders, so the code never pretends to be complete.

The project is currently backend-only. A frontend application, cloud object
storage, and production-grade moderation infrastructure are not included in
the current repository.

## Contents

- [Overview](#overview)
- [Current capabilities](#current-capabilities)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Running the backend](#running-the-backend)
- [Database and migrations](#database-and-migrations)
- [Testing](#testing)
- [API documentation](#api-documentation)
- [Project status and limitations](#project-status-and-limitations)
- [Development workflow](#development-workflow)
- [Security and data-safety notes](#security-and-data-safety-notes)

## Overview

The system supports a moderation-oriented video workflow:

1. A user registers and signs in.
2. The authenticated user uploads an MP4 video.
3. The backend validates the file and stores it locally.
4. A background analysis task runs the NSFW-Detection pipeline and stores the
   resulting label and confidence. Videos with a risk label enter the
   moderation queue.
5. Published videos are available through the public feed.
6. Users can report videos.
7. Moderators and admins can review queues and make moderation decisions.
8. Admins can manage user status and the roles supported by the current model.

The AI entry point is `run_video_analysis` in
[backend/app/services.py](backend/app/services.py), which calls
`app.ai.pipeline.analyse_video`. The Adult detector shells out to
`backend/NSFW-Detection/src/proposed/proposed_adult_video_detect.py` and reads its
`08_final_decision.json` output; no external AI API or Cloud Storage is used.

## Current capabilities

### Implemented and tested

- User registration and JWT login.
- Authenticated profile retrieval.
- Role model with `user`, `moderator`, and `admin`.
- MP4 upload with:
  - `.mp4` filename and `video/mp4` MIME validation.
  - 50 MiB size limit.
  - MP4 `ftyp`/brand/codec validation.
  - Local filesystem storage.
- AI content analysis (`run_video_analysis` → `app.ai.pipeline`):
  - Adult detection runs the NSFW-Detection pipeline in a subprocess and reads
    its `08_final_decision.json` result.
  - `AI_ANALYSIS_MODE=auto` (default): if the AI environment is unavailable the
    job records the reason in the transcript and falls back to the mock result.
  - `AI_ANALYSIS_MODE=required`: the job is marked `failed` when the AI
    environment is unavailable; `off` keeps the old mock-only behaviour.
  - A detected risk label (`Adult`) moves the video to `pending_review`; a
    normal result publishes it with a `Safe` label and its confidence.
  - Mock fallback result: development transcript, `Safe` label, confidence
    `0.95`, level `HIGH`.
- User video listing, public feed, and owner-only soft delete.
- Content reports with validation and duplicate-open-report protection.
- Moderation queue, open-report list, and moderation decisions.
- Admin MVP:
  - User list and search.
  - User detail.
  - Activate/deactivate user.
  - Moderator/admin list.
  - Role changes for the enum values supported by the model.
- Session management (UC001–UC002):
  - Refresh tokens with rotation (`POST /api/v1/auth/refresh`).
  - Logout revoking the current access token (`jti`) and, when supplied, the
    paired refresh token (`POST /api/v1/auth/logout`).
  - Password reset tokens (`forgot`/`reset`, 30 minutes, single use). Because
    no mail provider is integrated, `reset_token` is only echoed in the
    response when `environment` is not `production`.
- Profile update (`PATCH /api/v1/profile`): display name and password change;
  a password change revokes every refresh token.
- Video playback `GET /api/v1/videos/{id}/stream` with HTTP Range support.
- Label search `GET /api/v1/videos/search` (`label`, `exclude_label`, `q`,
  `limit`) returning each video's labels and owner.
- Label confirmation/editing: owner `POST /videos/{id}/labels/confirm`,
  moderator/admin `PATCH /videos/{id}/labels` (multi-label replace).
- Appeals (UC011/UC017): create, moderated list, approve/reject decision; an
  approved appeal publishes the video again. One open appeal per
  (video, user) is enforced by a partial unique index.
- Admin label management (2.2.13): list, create, rename, activate/deactivate,
  with video counts.
- Admin video status (2.2.12): publish, re-review, reject or soft-delete.
- Statistics (UC019/UC020): per-moderator counters and a `days`-window
  dashboard (videos by status, label distribution, reports/appeals/jobs,
  moderator workload).

### Partially implemented

- Moderation has no locking/claim workflow or complete audit history.
- Admin management does not yet include Senior Moderator, notifications,
  audit logs, workload statistics, or locked-work reassignment.
- Password reset has no mail delivery: outside `production` the reset token is
  returned in the response so the flow can be exercised locally.
- List endpoints have no pagination; only `/videos/search` caps results with
  `limit`.

### Detector placeholders

Detector placeholders (they raise `DetectorNotImplementedError` when called and
are recorded in the job transcript as skipped) live in
[backend/app/ai/placeholders.py](backend/app/ai/placeholders.py), with empty
model directories under `backend/NSFW-Detection/src/models/{violence,sound,text}/`.

### Not implemented in the current repository

- Frontend application.
- Speech-to-Text and the violence, sound and text detectors (placeholders only).
- Cloud video storage and email delivery for password reset.
- Pagination/filtering for the feed, video, report and moderation-queue lists.
- Moderation claim/locking, a full audit log, notifications and a job queue.

These status statements describe the current codebase, not a promise that the
corresponding SRS use cases are complete.

## Architecture

```mermaid
flowchart LR
    Client[Postman / API client] --> API[FastAPI application]
    API --> Auth[JWT and RBAC]
    API --> ORM[SQLAlchemy]
    ORM --> DB[(Neon PostgreSQL)]
    API --> Storage[Local upload directory]
    API --> Task[FastAPI BackgroundTasks]
    Task --> AI[run_video_analysis]
    AI --> Pipeline[app.ai.pipeline]
    Pipeline --> NSFW[NSFW-Detection subprocess]
    Pipeline --> Fallback[Mock fallback]
    NSFW --> ORM
    Fallback --> ORM
```

The test fixture uses a separate SQLite database and `test_storage`
directory so the test suite does not require destructive operations against the
online Neon database. The running backend reads `DATABASE_URL` from
`backend/.env`, which is filled in from `local/neondb.txt`.

## Technology stack

| Area | Technology verified in the repository |
|---|---|
| Language/runtime | Python; the development environment used Python 3.12 |
| API | FastAPI |
| Server | Uvicorn |
| Validation/settings | Pydantic and `pydantic-settings` |
| ORM | SQLAlchemy 2.x |
| Database | Neon PostgreSQL (online) with `psycopg[binary]`; URL from `local/neondb.txt` |
| Migrations | Alembic |
| Authentication | PyJWT and `hashlib.scrypt` password hashing |
| Background processing | FastAPI `BackgroundTasks` |
| AI content analysis | NSFW-Detection pipeline (TensorFlow 2.20 + PyTorch 2.6) run as a subprocess |
| Automated tests | Pytest and FastAPI TestClient |
| API collections | Postman/Newman local collections |

Dependency ranges are maintained in
[backend/requirements.txt](backend/requirements.txt). AI dependencies live in
[backend/NSFW-Detection/src/requirements.txt](backend/NSFW-Detection/src/requirements.txt) and
are installed separately so the API environment stays small.

## Repository structure

```text
.
├── backend/                      # Backend (FastAPI)
│   ├── app/
│   │   ├── config.py          # Settings and environment loading
│   │   ├── db.py              # SQLAlchemy engine/session setup
│   │   ├── dependencies.py    # JWT authentication and RBAC dependencies
│   │   ├── main.py            # FastAPI application and route handlers
│   │   ├── models.py          # SQLAlchemy models and enums
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── security.py        # Password hashing and JWT creation
│   │   ├── services.py        # Job lifecycle: NSFW pipeline + mock fallback
│   │   └── ai/
│   │       ├── base.py        # Detection/AnalysisReport contract
│   │       ├── nsfw.py        # NSFW-Detection subprocess adapter
│   │       ├── placeholders.py# Violence/sound/text detectors (not implemented)
│   │       └── pipeline.py    # Runs every detector, records skipped ones
│   ├── NSFW-Detection/
│   │   └── src/
│   │       ├── proposed/      # Adult detection pipeline (4 stages)
│   │       ├── models/        # Adult models + {violence,sound,text}/ placeholders
│   │       ├── requirements.txt  # CPU dependencies (pruned to what src/ imports)
│   │       └── README.md      # Pipeline usage, configuration, benchmarks
│   ├── alembic/versions/      # Database migrations
│   ├── scripts/check_db.py    # Non-destructive database connectivity check
│   ├── tests/                 # Official Pytest suite
│   ├── .env.example           # Safe configuration template (.env is ignored)
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/                  # Frontend (chưa có mã nguồn; SRS dùng ReactJS)
├── local/                     # Toàn bộ bị Git bỏ qua
│   ├── SRS.docx               # Tài liệu yêu cầu chính thức
│   ├── neondb.txt             # Chuỗi kết nối Neon PostgreSQL
│   └── TestDataset-v2/        # Bộ video test (Adult/, Normal/)
├── local-tests/               # Postman collections và module log (bị Git bỏ qua)
├── API_ENDPOINTS_GUIDE.md     # Detailed endpoint integration guide
├── PBL6_Implementation_Report.md
├── AGENTS.md                  # Project instructions for contributors/agents
├── README.md
├── pyproject.toml             # Python 3.14 project metadata (uv)
└── .python-version
```

`local/` is ignored as a whole, so `SRS.docx`, `neondb.txt` and
`TestDataset-v2/` can never be committed by accident. Postman collections,
module logs under `local-tests/`, runtime data and secrets are excluded from
Git as well.

## Prerequisites

Install or make available:

- Python 3.14 for the backend (`.python-version` and `requires-python >= 3.14`);
  Python 3.14.8 is the verified interpreter in this workspace.
- Access to the Neon PostgreSQL connection string stored in `local/neondb.txt`.
- Optional — only to run the real Adult pipeline: a second interpreter (Python
  3.11 recommended) with the NSFW-Detection dependencies installed, selected via
  `NSFW_PYTHON`. TensorFlow 2.20 does not support Python 3.14, so the AI
  environment is intentionally kept separate from the API environment.
- Git.
- Newman if API collection tests are required.

PowerShell is used in the examples below. Do not use production credentials or
production databases for local development or tests.

## Local setup

### 1. Clone and create a virtual environment

```powershell
git clone https://github.com/Hrk9324/PBL6_AI_short_video_moderation.git
Set-Location PBL6_AI_short_video_moderation

py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

If `py -3.14` is not available, use an installed Python version compatible
with the dependency ranges and keep the selected interpreter consistent for
installation, migrations, and tests.

### 2. Database: online Neon PostgreSQL

The Docker Compose PostgreSQL service has been removed from this repository.
The backend connects to the online Neon database described by
`local/neondb.txt`; the whole `local/` directory is ignored by Git.

No local database process is required. `backend/scripts/check_db.py` is a
non-destructive way to verify the connection:

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
python -m scripts.check_db
```

Expected output includes `database=neondb` and `user=neondb_owner`.

### 3. Configure environment variables

From the `backend` directory:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with local values. Copy `DATABASE_URL` from `local/neondb.txt`;
the safe template contains:

```dotenv
# Lấy từ local/neondb.txt — không commit file này
DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxx.aws.neon.tech/neondb?sslmode=require
SECRET_KEY=replace-with-a-long-random-development-secret-key
UPLOAD_DIR=storage/uploads
MAX_UPLOAD_SIZE_BYTES=52428800

# Chế độ phân tích AI: auto | required | off
AI_ANALYSIS_MODE=auto
# Interpreter chạy pipeline NSFW-Detection (TF 2.20 cần Python 3.11)
NSFW_PYTHON=
# Thư mục này tương đối so với backend/
NSFW_PIPELINE_DIR=NSFW-Detection/src
NSFW_TIMEOUT_SECONDS=600
```

Use URL encoding for reserved characters in a connection URL password. Never
commit `.env`, `local/neondb.txt` or share real credentials. The application reads
settings from the backend working directory.

### 4. Apply migrations

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
alembic current
alembic upgrade head
alembic current
```

Migrations are `0001_initial` (users, videos, labels, video labels, AI jobs,
moderation reviews, reports) and `0002_session_appeals` (refresh tokens,
revoked access tokens, password reset tokens, appeals). Both are already
applied to the Neon database in this workspace, so `alembic current` must
report `0002_session_appeals (head)`.

Do not drop or reset a database to resolve a migration problem. Check the
database URL, role permissions, schema, and current Alembic revision first.

## Running the backend

From `backend` with the virtual environment active:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify readiness from another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```json
{"status": "ok"}
```

FastAPI's generated documentation is available at
<http://127.0.0.1:8000/docs> while the server is running. The OpenAPI JSON is
available at <http://127.0.0.1:8000/openapi.json>.

## Testing

### Pytest

Run the official backend test suite:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q
```

The test fixture uses SQLite and local `test_storage`; it resets only
that test database through the fixture. It does not reset the online Neon
database. Besides the API tests, `tests/test_ai_integration.py` covers the NSFW
adapter's confidence parsing, the pipeline's skipped (not implemented)
detectors, the mock fallback and the `required` mode failure path;
`test_auth_session.py`, `test_video_stream_search.py` and
`test_labels_appeals_admin.py` cover logout/refresh/password reset, profile
updates, Range streaming, label search, label editing, appeals and admin
statistics.

The latest verified run in this workspace was:

- `42 passed, 3 warnings`
- The `real_video_path` fixture reads `local/TestDataset-v2/` (recursive), so
  the full API suite runs with real videos from the dataset.
- Warnings are deprecations from FastAPI/Starlette and did not fail tests.

### Newman

Newman collections are local-only and ignored by Git. With the backend running
on a local port, run a collection such as:

```powershell
Set-Location ..
newman run .\local-tests\postman\auth-jwt_v1.0.0.postman_collection.json `
  --env-var "base_url=http://127.0.0.1:8000"
```

Collections exist for Auth/JWT, User Profile, Video Upload, Video Management,
AI Analysis, Content Report, Moderation, and Admin Management. Their detailed
logs remain under `local-tests/logs/` and must not be committed.

Verified local Newman results recorded in the module logs include:

| Collection | Result |
|---|---|
| Auth/JWT | 7 requests, 10 assertions, 0 failed |
| User Profile | 5 requests, 5 assertions, 0 failed |
| Video Upload | 6 requests, 6 assertions, 0 failed |
| Video Management | 10 requests, 10 assertions, 0 failed |
| AI Analysis | 9 requests, 9 assertions, 0 failed |
| Content Report | 8 requests, 8 assertions, 0 failed |
| Moderation | 11 requests, 11 assertions, 0 failed |
| Admin Management | 11 requests, 11 assertions, 0 failed |

These results are historical local evidence recorded in module logs, not a CI
badge or a guarantee for every future environment.

## API documentation

See [API_ENDPOINTS_GUIDE.md](API_ENDPOINTS_GUIDE.md) for the complete,
source-verified request guide. It includes:

- All registered endpoints and operation IDs.
- Authentication and role requirements.
- JSON, query, path, and multipart request formats.
- Upload rules and local storage behavior.
- Response examples and implementation-backed errors.
- Postman/cURL examples and workflow sequences.
- A distinction between runtime-tested and source/OpenAPI-only behavior.

## Project status and limitations

The repository is a working backend MVP, not a complete production platform.
The main known limitations are:

- No frontend application is present.
- The Adult pipeline only runs when its own Python environment (TensorFlow,
  PyTorch, OpenCV) is installed and selected with `NSFW_PYTHON`; otherwise the
  job records the reason in its transcript and falls back to the mock result.
- Speech-to-text and the violence, sound and text detectors are placeholders
  (`DetectorNotImplementedError`) with empty model directories.
- Uploads are local filesystem files; there is no cloud storage adapter, and
  password reset has no mail delivery (the token is echoed only outside
  `production`).
- Feed, report and moderation-queue lists have no pagination; only
  `/videos/search` accepts `limit`.
- Moderation lacks robust locking, concurrency handling, evidence management,
  and a complete audit log.
- Notifications and production job queues are absent; statistics cover the
  requested `days` window only.
- Admin management lacks Senior Moderator, notification, session-revocation
  and locked-work reassignment behavior.
- Schema changes go through reviewed Alembic migrations (currently
  `0002_session_appeals`).

The authoritative requirement document is `local/SRS.docx`. It is not
tracked in Git. The implementation report and API guide describe the current
gap between that SRS and the implemented MVP.

## Development workflow

Before changing behavior:

1. Read [AGENTS.md](AGENTS.md), the relevant SRS section, and
   [API_ENDPOINTS_GUIDE.md](API_ENDPOINTS_GUIDE.md).
2. Inspect the existing route, schema, model, dependency, migration, and test.
3. Make a focused change without overwriting unrelated working-tree changes.
4. Add or update official Pytest coverage.
5. Run Pytest and, for API modules, the corresponding local Newman collection.
6. Record module test history under the ignored local log directory.
7. Update the API guide when the public contract changes.
8. Review `git diff`, `git diff --check`, and staged file names before any
   explicitly authorized commit.

Every new module requires explicit user approval before implementation. Do not
automatically select or start the next module after completing one.

## Security and data-safety notes

- Never commit `.env`, `local/neondb.txt`, passwords, JWTs, API keys, database
  dumps, local media, Postman environments, or runtime logs.
- Do not use production credentials or a production database for local tests.
- The Neon connection string in `local/neondb.txt` is a secret: keep it out of
  Git, chat logs and screenshots (`local/` is ignored as a whole).
- Do not reset, drop, truncate, or delete a database to fix a connection or
  migration issue.
- Keep the SRS and internal development artifacts local.
- Review `.gitignore` and `git status --short` before committing.

## License and team

No license or team metadata has been confirmed in the repository. No license
statement is made here.
