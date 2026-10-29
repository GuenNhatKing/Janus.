# Database and Migration Guide

## Connection

The backend reads `DATABASE_URL` from `backend\.env` using
`pydantic-settings`. PostgreSQL URLs beginning with `postgresql://` are
normalized to the `psycopg` SQLAlchemy dialect.

Verify without exposing credentials:

```powershell
Set-Location E:\PBL6\backend
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe scripts\check_db.py
.\.venv\Scripts\alembic.exe current
```

The verified Neon database is `neondb`; the current revision is
`0002_session_appeals (head)`.

## Schema

`0001_initial` creates users, labels, videos, AI jobs, video labels,
moderation reviews, and reports. `0002_session_appeals` adds refresh tokens,
revoked access tokens, password reset tokens, and appeals.

Important relationships:

- `users.id -> videos.owner_id`
- `videos.id -> ai_jobs.video_id`
- `videos.id -> video_labels.video_id`
- `labels.id -> video_labels.label_id`
- `videos.id -> reports.video_id`
- `videos.id -> moderation_reviews.video_id`
- `videos.id -> appeals.video_id`

## Migration safety

```powershell
.\.venv\Scripts\alembic.exe current
.\.venv\Scripts\alembic.exe upgrade head
```

Do not use database reset, drop, truncate, bulk deletion, or destructive
downgrade as troubleshooting shortcuts. Review the migration and data impact
first. The official Neon database is shared by development/API verification.

## Read-only verification

Use SQLAlchemy scripts or a trusted SQL client for read-only checks such as:

```sql
SELECT current_database(), current_user;
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';
```

Never print the connection URL, password, JWT, or reset token.
