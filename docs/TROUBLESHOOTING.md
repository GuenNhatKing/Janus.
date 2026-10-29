# Troubleshooting

## Backend does not start

Check the selected interpreter and import:

```powershell
Set-Location E:\PBL6\backend
uv run python -c "import app.main; print('import ok')"
```

Then inspect `.env` names, the upload directory, and the server stderr. Do not
print secret values.

## Database connection failure

```powershell
uv run python scripts\check_db.py
uv run alembic current
```

Check host, port, SSL mode, role permissions, and whether the Neon database is
reachable. Do not switch to SQLite for API verification or reset the database.

## Migration mismatch

Read `alembic current`, inspect the migration files, and verify that
`DATABASE_URL` points to the intended Neon database. Apply only reviewed
additive migrations with `alembic upgrade head`.

## Upload returns 422

The endpoint requires a multipart field named `file`. `caption` is a query
parameter:

```text
POST /api/v1/videos?caption=Example
multipart field: file=<video.mp4>
```

Use `video/mp4`, an `.mp4` filename, a valid MP4 `ftyp` box, a supported codec,
and a file no larger than 50 MiB.

## AI job remains running or fails

Poll `GET /api/v1/videos/{video_id}/ai`. CPU inference for the verified sample
took about 11 seconds, so a single immediate read can legitimately return
`running`.

For real inference, use `AI_ANALYSIS_MODE=required` and check:

- both model files exist;
- the interpreter has TensorFlow, Keras, PyTorch, OpenCV, and NumPy;
- `NSFW_PIPELINE_DIR` resolves to `backend\NSFW-Detection\src`;
- `NSFW_TIMEOUT_SECONDS` is sufficient;
- `PYTHONUTF8=1` avoids Windows console encoding failures from Vietnamese
  logger messages.

## API returns 401 or 403

- `401`: missing/invalid/expired/revoked JWT, or inactive account.
- `403`: valid user but insufficient role.

Do not grant Admin/Moderator roles directly on Neon without approval.

## Newman cannot find a video

Run Newman from `backend` and use the repository collection paths. The current
upload fixture is `..\local\TestDataset-v2\Travel_4.mp4` relative to `backend`.

## API succeeds but database appears unchanged

Poll the AI job until terminal state, then use a read-only query by the
returned `video_id`. Check `videos`, `ai_jobs`, and `video_labels`. Do not
retry by deleting records or resetting the schema.

## Model files are missing

The model files are intentionally ignored by Git. Obtain approved artifacts
and place them under `backend\NSFW-Detection\src\models\`; do not replace them
with empty directories or an unverified download.
