# PBL6 Project Guidelines

## Requirements and scope

- Treat `local/SRS.docx` as the authoritative product requirement document. It
  is local-only (`local/` is ignored by Git) and must not be committed.
- Treat the current FastAPI source as the authority for implemented behavior;
  do not invent endpoints, schemas, permissions, or test results.
- Keep `API_ENDPOINTS_GUIDE.md` synchronized with source, OpenAPI, and verified
  runtime behavior.
- Preserve the distinction between implemented, partially implemented,
  unverified, and blocked SRS requirements.

## Architecture

- Backend entry point: `backend/app/main.py`.
- Pydantic request/response schemas: `backend/app/schemas.py`.
- SQLAlchemy models and enums: `backend/app/models.py`.
- Authentication and RBAC: `backend/app/security.py` and
  `backend/app/dependencies.py`.
- Database setup and sessions: `backend/app/db.py`; migrations are under
  `backend/alembic/`.
- Current AI processing is a local mock adapter. Do not add external AI or
  cloud-storage calls unless explicitly requested.

## Build and test

- Use the project interpreter:
  `backend\.venv\Scripts\python.exe -m pytest -q`
- Run Newman only with local collections under `local-tests\postman\` and a
  local backend. Do not send test data to production or external services.
- Keep one Markdown module log under `local-tests\logs\` per module. These
  collections, logs, reports, fixtures, and local datasets are ignored by Git.
- Check backend health and database/migration state before API tests when the
  environment permits.

## Change and data-safety conventions

- Make surgical changes and preserve unrelated uncommitted work.
- Do not reset, drop, truncate, or delete databases or user data.
- Do not commit `.env`, credentials, JWTs, local media, SRS, Postman exports,
  runtime logs, or generated artifacts.
- Keep official source, migrations, safe configuration examples, official
  automated tests, README/project documentation, and `API_ENDPOINTS_GUIDE.md`
  tracked.
- Before any commit, inspect staged names and run `git diff --check`; never
  stage the whole workspace blindly.
- Do not commit or push unless the user explicitly requests it.

## Module approval gate

- Do not select or start a new module automatically.
- Before implementing any new module, report the proposed scope, SRS
  requirements, dependencies, risks, and planned work, then wait for explicit
  user approval.
- Once a module is approved, stay within that scope. Ask before changing an
  unrelated module or expanding requirements.
- After the current module is verified, stop and wait for the next instruction.
