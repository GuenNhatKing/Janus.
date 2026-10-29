# PBL6 Documentation Index

Updated: 2026-10-28

This index separates operational guidance from historical evidence. Claims in
the current guides are based on the FastAPI source, the current OpenAPI
surface, and the Newman/independent AI runs recorded in
`local-tests/logs/`.

## For users and operators

- [USER_GUIDE.md](USER_GUIDE.md) — setup, configuration, startup, user
  workflows, and known limitations.
- [API_GUIDE.md](API_GUIDE.md) — verified API contract, authentication,
  request examples, and endpoint status.
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — confirmed startup, database,
  upload, AI, authentication, and Newman diagnostics.

## For developers

- [ARCHITECTURE.md](ARCHITECTURE.md) — backend, storage, background task, and
  AI pipeline structure.
- [DATABASE.md](DATABASE.md) — PostgreSQL Neon, SQLAlchemy models, migrations,
  and data-safety rules.
- [AI_MODEL.md](AI_MODEL.md) — model files, preprocessing, inference,
  fallback modes, and evidence from the real inference run.
- [TESTING.md](TESTING.md) — Newman collections, independent scripts, SQL
  verification, and test result classification.

## Historical and source documents

- [../README.md](../README.md) — short project introduction and quick start.
- [../API_ENDPOINTS_GUIDE.md](../API_ENDPOINTS_GUIDE.md) — retained historical
  API reference; use [API_GUIDE.md](API_GUIDE.md) when the two differ.
- [../PBL6_Implementation_Report.md](../PBL6_Implementation_Report.md) —
  earlier implementation report. Some historical sections predate the real
  AI integration and should not override current runtime evidence.
- [../backend/NSFW-Detection/src/README.md](../backend/NSFW-Detection/src/README.md)
  — source-level pipeline and benchmark notes.
- `local/SRS.docx` — local authoritative requirements source; not tracked and
  not reproduced in this repository.
- `local-tests/logs/` — immutable-style local test evidence and audit logs;
  ignored by Git.

## Status vocabulary

- `WORKING`: exercised successfully in the current environment.
- `PARTIAL`: a usable path exists but important behavior is incomplete.
- `BLOCKED`: execution requires unavailable permission, role, or resource.
- `NOT_IMPLEMENTED`: the source explicitly contains a placeholder or absent
  implementation.
- `NOT_VERIFIED`: source exists but no suitable runtime evidence is available.
