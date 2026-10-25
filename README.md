# PBL6 — AI Short Video Moderation Platform

PBL6 is a FastAPI backend MVP for a short-video platform with JWT
authentication, local video storage, mock AI analysis, user reports, and basic
moderation workflows.

The project is currently backend-only. A frontend application, production AI
provider, cloud object storage, and production-grade moderation infrastructure
are not included in the current repository.

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
4. A local mock analysis task creates a transcript and a `Safe` label.
5. Published videos are available through the public feed.
6. Users can report videos.
7. Moderators and admins can review queues and make moderation decisions.
8. Admins can manage user status and the roles supported by the current model.

The implementation is intentionally local-only for development. The AI adapter
is `run_mock_analysis`; no external AI API or Cloud Storage integration is
present in the current backend.

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
- Mock asynchronous AI result:
  - Development transcript.
  - `Safe` label.
  - Confidence `0.95`, level `HIGH`.
- User video listing, public feed, and owner-only soft delete.
- Content reports with validation and duplicate-open-report protection.
- Moderation queue, open-report list, and moderation decisions.
- Admin MVP:
  - User list and search.
  - User detail.
  - Activate/deactivate user.
  - Moderator/admin list.
  - Role changes for the enum values supported by the model.

### Partially implemented

- Moderation has no locking/claim workflow or complete audit history.
- Admin management does not yet include Senior Moderator, notifications,
  audit logs, session revocation, workload statistics, or locked-work
  reassignment.
- Video management has no pagination, search/filtering, or streaming endpoint.
- Authentication has no refresh token, logout/revocation, or password recovery.

### Not implemented in the current repository

- Frontend application.
- Real AI, speech-to-text, or external model-provider integration.
- Cloud video storage.
- Appeal workflow.
- Full admin policy/label management.
- Analytics dashboard and production job infrastructure.

These status statements describe the current codebase, not a promise that the
corresponding SRS use cases are complete.

## Architecture

```mermaid
flowchart LR
    Client[Postman / API client] --> API[FastAPI application]
    API --> Auth[JWT and RBAC]
    API --> ORM[SQLAlchemy]
    ORM --> DB[(PostgreSQL)]
    API --> Storage[Local upload directory]
    API --> Task[FastAPI BackgroundTasks]
    Task --> MockAI[run_mock_analysis]
    MockAI --> ORM
```

The automated test fixture uses a separate SQLite database and `test_storage`
directory so the test suite does not require destructive operations against the
development PostgreSQL database. The running backend uses the database URL
configured in `.env`.

## Technology stack

| Area | Technology verified in the repository |
|---|---|
| Language/runtime | Python; the development environment used Python 3.12 |
| API | FastAPI |
| Server | Uvicorn |
| Validation/settings | Pydantic and `pydantic-settings` |
| ORM | SQLAlchemy 2.x |
| Database | PostgreSQL with `psycopg[binary]` |
| Migrations | Alembic |
| Authentication | PyJWT and `hashlib.scrypt` password hashing |
| Background processing | FastAPI `BackgroundTasks` |
| Automated tests | Pytest and FastAPI TestClient |
| API collections | Postman/Newman local collections |
| Optional database runtime | Docker Compose PostgreSQL |

Dependency ranges are maintained in
[backend/requirements.txt](backend/requirements.txt).

## Repository structure

```text
.
├── backend/
│   ├── app/
│   │   ├── config.py          # Settings and environment loading
│   │   ├── db.py              # SQLAlchemy engine/session setup
│   │   ├── dependencies.py    # JWT authentication and RBAC dependencies
│   │   ├── main.py            # FastAPI application and route handlers
│   │   ├── models.py          # SQLAlchemy models and enums
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── security.py        # Password hashing and JWT creation
│   │   └── services.py        # MP4 validation and mock AI adapter
│   ├── alembic/
│   │   └── versions/          # Database migrations
│   ├── scripts/
│   │   └── check_db.py        # Non-destructive database connectivity check
│   ├── tests/                 # Official Pytest suite
│   ├── .env.example           # Safe configuration template
│   ├── alembic.ini
│   └── requirements.txt
├── docker/
│   └── postgres/              # PostgreSQL initialization script
├── docker-compose.yml         # Optional local PostgreSQL service
├── API_ENDPOINTS_GUIDE.md     # Detailed endpoint integration guide
├── PBL6_Implementation_Report.md
├── AGENTS.md                  # Project instructions for contributors/agents
└── README.md
```

`SRS.docx`, `TestDataset/`, Postman collections, test logs, local workspaces,
runtime data, and secrets are local development resources and are excluded
from Git where appropriate.

## Prerequisites

Install or make available:

- Python compatible with the dependency ranges; Python 3.12 is the verified
  development runtime.
- PostgreSQL 16 or a compatible PostgreSQL installation, or Docker Desktop for
  the optional Compose setup.
- Git.
- Newman if API collection tests are required.

PowerShell is used in the examples below. Do not use production credentials or
production databases for local development or tests.

## Local setup

### 1. Clone and create a virtual environment

```powershell
git clone https://github.com/Hrk9324/PBL6_AI_short_video_moderation.git
Set-Location PBL6_AI_short_video_moderation

Set-Location backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If `py -3.12` is not available, use an installed Python version compatible
with the dependency ranges and keep the selected interpreter consistent for
installation, migrations, and tests.

### 2. Prepare PostgreSQL

Use an existing local PostgreSQL installation or the optional Docker Compose
service. For native PostgreSQL, create a development database and a dedicated
application role; do not use the PostgreSQL superuser as the application
runtime identity in normal environments.

For Docker Compose, set private PowerShell variables and start PostgreSQL:

```powershell
Set-Location ..
$env:POSTGRES_ADMIN_PASSWORD = "CHANGE_ME_ADMIN_PASSWORD"
$env:POSTGRES_APP_PASSWORD = "CHANGE_ME_APP_PASSWORD"
docker compose up -d postgres
docker compose ps
docker compose logs postgres
```

The Compose initialization script runs only when the PostgreSQL volume is
created for the first time. Stop and start the service without deleting data:

```powershell
docker compose stop postgres
docker compose start postgres
```

Do not use `docker compose down -v` unless intentionally removing the database
volume and its data.

### 3. Configure environment variables

From the `backend` directory:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with local values. The safe template contains:

```dotenv
DATABASE_URL=postgresql+psycopg://pbl6_app:YOUR_PASSWORD@localhost:5432/pbl6
SECRET_KEY=replace-with-a-long-random-development-secret-key
UPLOAD_DIR=storage/uploads
MAX_UPLOAD_SIZE_BYTES=52428800
```

Use URL encoding for reserved characters in a connection URL password. Never
commit `.env` or share real credentials. The application reads settings from
the backend working directory.

### 4. Apply migrations

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
alembic current
alembic upgrade head
alembic current
```

The current migration is `0001_initial`. It creates the users, videos, labels,
video labels, AI jobs, moderation reviews, and reports tables.

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

The current test fixture uses SQLite and local `test_storage`; it resets only
that test database through the fixture. It does not reset the development
PostgreSQL database.

The latest verified development run before this README rewrite was:

- `14 passed, 3 warnings`
- Warnings are deprecations from FastAPI/Starlette/httpx and did not fail tests.

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
- AI and speech-to-text are mock-only.
- Uploads are local filesystem files; there is no cloud storage adapter.
- No video streaming/playback endpoint is implemented.
- No pagination, search, or label filtering for the public/user video lists.
- No refresh/revocation/logout/password-recovery workflow.
- Moderation lacks robust locking, concurrency handling, evidence management,
  and a complete audit log.
- Appeal, notifications, analytics, and production job queues are absent.
- Admin management is an MVP and lacks Senior Moderator, audit, notification,
  session-revocation, workload-statistics, and locked-work reassignment
  behavior.
- The current database migration is an initial schema migration; future
  schema changes require reviewed Alembic migrations.

The authoritative requirement document is the local `SRS.docx`. It is not
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

- Never commit `.env`, passwords, JWTs, API keys, database dumps, local media,
  Postman environments, or runtime logs.
- Use a least-privilege PostgreSQL application role.
- Do not use production credentials or a production database for local tests.
- Do not reset, drop, truncate, or delete a database to fix a connection or
  migration issue.
- Keep the SRS and internal development artifacts local.
- Review `.gitignore` and `git status --short` before committing.

## License and team

No license or team metadata has been confirmed in the repository. No license
statement is made here.
