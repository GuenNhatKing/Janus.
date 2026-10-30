# PBL6 Architecture

## Runtime flow

```text
HTTP client / Newman
        |
FastAPI app.main
        |
JWT/RBAC dependencies ---- SQLAlchemy Session ---- PostgreSQL Neon
        |
Upload file -> local UPLOAD_DIR + Video + AIJob
        |
FastAPI BackgroundTasks
        |
services.run_video_analysis
        |
app.ai.pipeline -> app.ai.nsfw subprocess
        |
NSFW-Detection proposed pipeline
  Stage 1 HSV sampling
  Stage 2 MobileNetV3 coarse filter
  Stage 3 diversity sampling
  Stage 4 ResNet-50 FCN dual-branch decision
        |
08_final_decision.json -> VideoLabel/AIJob/Video status
```

## Important source locations

- `backend/src/app/main.py`: route registration and request orchestration.
- `backend/src/app/schemas/`: Pydantic request/response contracts.
- `backend/src/app/models/`: SQLAlchemy models and enums.
- `backend/src/app/dependencies.py`: JWT validation and role checks.
- `backend/src/app/core/security.py`: password hashing, JWT, opaque token helpers.
- `backend/src/app/services/ai_service.py`: upload validation and AI job lifecycle.
- `backend/src/app/ai/nsfw.py`: subprocess adapter and preflight checks.
- `backend/src/app/ai/pipeline.py`: real NSFW detector plus placeholder detectors.
- `backend/NSFW-Detection/src/proposed/`: model loading and inference stages.
- `backend/alembic/versions/`: schema migrations.

## Status transitions

Upload creates a `processing` video and a pending AI job. Real safe analysis
adds `Safe` and publishes; a detected Adult label moves the video to
`pending_review`. Required-mode errors mark the job and video `failed`.
Reports can move a published video to `pending_review`; moderators/admins can
approve or reject it.

## Boundaries

The frontend is a separate Vite/React application under `frontend/`. The
repository still has no cloud storage, external AI API, mail provider,
distributed job queue, moderation lock, or full audit trail.
