# API and AI Testing Guide

The current workflow uses Newman/Postman, independent Python scripts, backend
logs, and read-only Neon queries. Pytest is not part of the current
verification workflow.

## Preconditions

```powershell
Set-Location E:\PBL6\backend
uv run python scripts\check_db.py
uv run alembic current
```

Start the backend with real inference:

```powershell
$env:AI_ANALYSIS_MODE="required"
$env:PROJ6_DEVICE="cpu"
$env:PYTHONUTF8="1"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Newman collections

Run from `backend` so relative upload paths resolve correctly:

```powershell
newman run ..\local-tests\postman\auth-jwt_v1.0.0.postman_collection.json
newman run ..\local-tests\postman\user-profile_v1.0.0.postman_collection.json
newman run ..\local-tests\postman\video-upload_v1.0.0.postman_collection.json
newman run ..\local-tests\postman\AI_Model_Integration.postman_collection.json --delay-request 1000
newman run ..\local-tests\postman\content-report_v1.0.0.postman_collection.json
newman run ..\local-tests\postman\video-management_v1.0.0.postman_collection.json
```

Moderation and admin collections require approved privileged accounts. If
those accounts are unavailable, mark the result `BLOCKED`; do not change Neon
roles to force a pass.

## Independent real inference

```powershell
$env:PROJ6_DEVICE="cpu"
$env:PYTHONUTF8="1"
uv run --project NSFW-Detection\src python NSFW-Detection\src\proposed\proposed_adult_video_detect.py `
  --video ..\local\TestDataset-v2\Travel_4.mp4 `
  --out_dir ..\local-tests\ai-real-inference-20261028
```

Inspect `08_final_decision.json` and confirm model-load, anchor, decision, and
timing evidence. Do not treat a mock transcript as real inference.

## Result meanings

- `PASS`: request/script ran and assertions plus persistence checks passed.
- `FAIL`: it ran but a required assertion or business result failed.
- `ERROR`: command could not execute.
- `BLOCKED`: required role, model, data, or permission was unavailable.
- `SKIPPED`: intentionally not run with a documented reason.

## Current evidence

The real AI collection passed with 18 requests and 23 assertions. Video Upload,
Content Report, and Video Management also passed in required mode. Evidence is
under `local-tests/logs/AI_Model_Real_DB_Test_2026-10-28.md`.
