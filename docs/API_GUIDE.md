# PBL6 API Guide

Updated: 2026-10-28

## 1. Base URL and authentication

Run the backend from the repository root with `uv`:

```powershell
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use `http://127.0.0.1:8000` as the base URL. Swagger UI is at `/docs`,
ReDoc at `/redoc`, and OpenAPI JSON at `/openapi.json`.

Register and login:

```powershell
$body = @{email="user@example.com"; display_name="Example"; password="password123"} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/api/v1/auth/register -Method Post -ContentType "application/json" -Body $body
$login = Invoke-RestMethod http://127.0.0.1:8000/api/v1/auth/login -Method Post -ContentType "application/json" -Body (@{email="user@example.com"; password="password123"} | ConvertTo-Json)
$headers = @{Authorization = "Bearer " + $login.access_token}
```

Never copy a real token, password, or connection string into documentation.

## 2. Common response and error rules

- `401`: missing, invalid, expired, revoked token, or inactive user.
- `403`: authenticated user lacks the required role.
- `404`: resource is absent, deleted, or not visible to the caller.
- `409`: duplicate account/report/appeal/label conflict.
- `422`: request schema, UUID, or required multipart field is invalid.
- `400`: business validation failure.
- `413`: upload exceeds the configured 50 MiB limit.
- `204`: successful operation with no response body.

## 3. Endpoint matrix

The following paths are taken from the runtime FastAPI route table. `VERIFIED`
means exercised in the current Newman/API evidence; `IMPLEMENTED_NOT_TESTED`
means source/OpenAPI verified only; `BLOCKED` requires a privileged account.

| Method | Path | Auth/role | Status |
|---|---|---|---|
| GET | `/health` | public | VERIFIED |
| POST | `/api/v1/auth/register` | public | VERIFIED |
| POST | `/api/v1/auth/login` | public | VERIFIED |
| GET | `/api/v1/profile` | authenticated | VERIFIED |
| PATCH | `/api/v1/profile` | authenticated | IMPLEMENTED_NOT_TESTED |
| POST | `/api/v1/auth/logout` | authenticated | IMPLEMENTED_NOT_TESTED |
| POST | `/api/v1/auth/refresh` | public + refresh token | IMPLEMENTED_NOT_TESTED |
| POST | `/api/v1/auth/password/forgot` | public | IMPLEMENTED_NOT_TESTED |
| POST | `/api/v1/auth/password/reset` | public + reset token | IMPLEMENTED_NOT_TESTED |
| POST | `/api/v1/videos` | authenticated | VERIFIED |
| GET | `/api/v1/videos` | authenticated/owner | VERIFIED |
| GET | `/api/v1/feed` | public | IMPLEMENTED_NOT_TESTED |
| GET | `/api/v1/videos/{video_id}/ai` | owner/moderator/admin | VERIFIED |
| GET | `/api/v1/videos/{video_id}/stream` | public/owner/moderator/admin by visibility | IMPLEMENTED_NOT_TESTED |
| DELETE | `/api/v1/videos/{video_id}` | owner | IMPLEMENTED_NOT_TESTED |
| GET | `/api/v1/videos/search` | authenticated | IMPLEMENTED_NOT_TESTED |
| POST | `/api/v1/videos/{video_id}/reports` | authenticated | VERIFIED |
| POST | `/api/v1/videos/{video_id}/labels/confirm` | owner | IMPLEMENTED_NOT_TESTED |
| PATCH | `/api/v1/videos/{video_id}/labels` | moderator/admin | BLOCKED |
| POST | `/api/v1/videos/{video_id}/appeals` | owner of rejected video | IMPLEMENTED_NOT_TESTED |
| GET | `/api/v1/moderation/queue` | moderator/admin | BLOCKED |
| POST | `/api/v1/moderation/videos/{video_id}/decision` | moderator/admin | BLOCKED |
| GET | `/api/v1/moderation/reports` | moderator/admin | BLOCKED |
| POST | `/api/v1/moderation/reports/{report_id}/decision` | moderator/admin | BLOCKED |
| GET | `/api/v1/moderation/appeals` | moderator/admin | BLOCKED |
| POST | `/api/v1/moderation/appeals/{appeal_id}/decision` | moderator/admin | BLOCKED |
| GET | `/api/v1/admin/users` | admin | BLOCKED |
| GET | `/api/v1/admin/users/{user_id}` | admin | BLOCKED |
| PATCH | `/api/v1/admin/users/{user_id}/status` | admin | BLOCKED |
| GET | `/api/v1/admin/moderators` | admin | BLOCKED |
| PATCH | `/api/v1/admin/users/{user_id}/role` | admin | BLOCKED |
| PATCH | `/api/v1/admin/videos/{video_id}/status` | admin | BLOCKED |
| GET | `/api/v1/admin/labels` | admin | BLOCKED |
| POST | `/api/v1/admin/labels` | admin | BLOCKED |
| PATCH | `/api/v1/admin/labels/{label_id}` | admin | BLOCKED |
| GET | `/api/v1/admin/moderators/{moderator_id}/stats` | admin | BLOCKED |
| GET | `/api/v1/admin/stats` | admin | BLOCKED |

No `GET /api/v1/videos/{video_id}` detail endpoint is registered. Use the
owner list, feed/search, AI endpoint, or stream endpoint as appropriate.

## 4. Upload and AI

Upload uses multipart form data. Do not manually set the multipart boundary:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/videos?caption=Travel" `
  -H "Authorization: Bearer <ACCESS_TOKEN>" `
  -F "file=@E:\PBL6\local\TestDataset-v2\Travel_4.mp4;type=video/mp4"
```

The response initially has status `processing`. Poll:

```text
GET /api/v1/videos/{video_id}/ai
```

The response contains `job_status`, `transcript`, and `labels`. With real
inference, the transcript contains `[NSFW-Detection]`; with fallback it
contains the mock transcript and an explanatory note. Terminal job states are
`succeeded` and `failed`.

## 5. Endpoint-specific contracts

The route matrix above identifies every operation. This section records the
request fields and response shape for operations that are not covered by the
upload example. Exact JSON field types are also available from `/openapi.json`.

| Operation | Request parameters/body | Successful response | Main implementation errors |
|---|---|---|---|
| `GET /api/v1/videos` | Bearer token | Array of owned `VideoResponse` | `401` |
| `GET /api/v1/feed` | Public | Array of published `VideoResponse` | Database/runtime `5xx` |
| `GET /api/v1/videos/{id}/ai` | UUID path, owner/moderator/admin token | `video_id`, `job_status`, `transcript`, `labels[]` | `401`, `404`, `422` |
| `GET /api/v1/videos/{id}/stream` | UUID path, visibility rules | Video bytes; supports Range | `401`, `404`, `416`/file errors |
| `DELETE /api/v1/videos/{id}` | UUID path, owner token | `204`; soft-deletes | `401`, `404`, `422` |
| `GET /api/v1/videos/search` | `label`, `exclude_label`, `q`, `limit=1..100` | `VideoSearchItem[]` with owner and labels | `401`, `422` |
| `PATCH /api/v1/profile` | `display_name` and/or `current_password` + `new_password` | `UserResponse` | `401`, `422`; wrong current password is `400` |
| `POST /api/v1/auth/logout` | Optional `{refresh_token}` | `204`; revokes current access JTI | `401`, `422` |
| `POST /api/v1/auth/refresh` | `{refresh_token}` | New access and rotated refresh token | `401`, `422` |
| `POST /api/v1/auth/password/forgot` | `{email}` | `202`; local non-production may include `reset_token` | `422` |
| `POST /api/v1/auth/password/reset` | `{token,new_password}` | `204` | `400`, `422` |
| `POST /api/v1/videos/{id}/reports` | `{reason}`; authenticated | `ReportResponse`, `201` | `401`, `404`, `409`, `422` |
| `POST /api/v1/videos/{id}/labels/confirm` | `{labels:[{name,confidence}]}`; owner | `VideoLabelInfo[]` | `400`, `401`, `404`, `422` |
| `POST /api/v1/videos/{id}/appeals` | `{reason}`; owner of rejected video | `AppealResponse`, `201` | `400`, `401`, `404`, `409`, `422` |
| `GET /api/v1/moderation/appeals` | Optional `status=open|approved|rejected` | `AppealResponse[]` | `401`, `403`, `422` |
| `POST /api/v1/moderation/appeals/{id}/decision` | `{action:approve|reject,reason?}` | `204` | `401`, `403`, `404`, `422` |
| `GET /api/v1/moderation/queue` | Moderator/admin token | `VideoResponse[]` pending review | `401`, `403` |
| `POST /api/v1/moderation/videos/{id}/decision` | `{action,reason?}` | `204`; creates review | `401`, `403`, `404`, `422` |
| `GET /api/v1/moderation/reports` | Moderator/admin token | Open `ReportResponse[]` | `401`, `403` |
| `POST /api/v1/moderation/reports/{id}/decision` | `{action,reason?}` | `204`; resolves/rejects report | `401`, `403`, `404`, `422` |
| `PATCH /api/v1/videos/{id}/labels` | `{labels:[...]}`; moderator/admin | `VideoLabelInfo[]` | `401`, `403`, `400`, `404`, `422` |
| `GET /api/v1/admin/users` | Optional `search`; admin token | `AdminUserSummary[]` | `401`, `403` |
| `GET /api/v1/admin/users/{id}` | UUID path; admin token | `AdminUserDetail` | `401`, `403`, `404`, `422` |
| `PATCH /api/v1/admin/users/{id}/status` | `{is_active}`; admin token | `AdminUserDetail` | `400`, `401`, `403`, `404`, `422` |
| `GET /api/v1/admin/moderators` | Admin token | `AdminUserSummary[]` | `401`, `403` |
| `PATCH /api/v1/admin/users/{id}/role` | `{role:user|moderator|admin}` | `AdminUserDetail` | `400`, `401`, `403`, `404`, `422` |
| `PATCH /api/v1/admin/videos/{id}/status` | `{status,reason?}`; status is `pending_review|published|rejected|deleted` | `VideoResponse` | `401`, `403`, `404`, `422` |
| `GET /api/v1/admin/labels` | Admin token | `AdminLabelResponse[]` | `401`, `403` |
| `POST /api/v1/admin/labels` | `{name}`; admin token | `AdminLabelResponse`, `201` | `401`, `403`, `409`, `422` |
| `PATCH /api/v1/admin/labels/{id}` | `{name?}` and/or `{is_active?}` | `AdminLabelResponse` | `401`, `403`, `404`, `409`, `422` |
| `GET /api/v1/admin/moderators/{id}/stats` | UUID path; admin token | `ModeratorStatsResponse` | `401`, `403`, `404`, `422` |
| `GET /api/v1/admin/stats` | `days=1..365`; admin token | `SystemStatsResponse` | `401`, `403`, `422` |

## 6. Reports and moderation

Create a report:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/videos/<VIDEO_ID>/reports" `
  -H "Authorization: Bearer <ACCESS_TOKEN>" `
  -H "Content-Type: application/json" `
  -d "{\"reason\":\"Reason with at least three characters\"}"
```

An open report can move a published video to `pending_review`. Moderator/admin
decision endpoints accept:

```json
{"action":"approve","reason":"review note"}
```

The implementation uses the existing `approve`/`reject` enums. Privileged
flows were not marked verified because no approved Moderator/Admin account was
available for Neon.

## 7. Newman

Collections are local-only under `local-tests\postman\`. The real model
collection is:

```powershell
Set-Location E:\PBL6\backend
newman run ..\local-tests\postman\AI_Model_Integration.postman_collection.json --delay-request 1000
```

The collection creates uniquely named test accounts and may leave test data in
Neon. Do not clean records without confirming ownership and approval.

## 8. Current verified evidence

- Auth/JWT and User Profile passed in prior Neon runs.
- Real AI collection: 18 requests, 23 assertions, 0 failures.
- Video Upload: 6 requests, 6 assertions, 0 failures.
- Content Report: 8 requests, 8 assertions, 0 failures.
- Video Management: 10 requests, 10 assertions, 0 failures.
- Real model result was persisted in Neon as `ai_jobs.succeeded`,
  `videos.published`, and a `Safe` video label.
