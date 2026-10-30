# Frontend
﻿# PBL6 frontend

This directory contains the Vite/React frontend for the PBL6 short-video
moderation platform.

## Run locally

```powershell
Set-Location E:\PBL6\frontend
npm install
npm run dev
```

The Vite development server prints its local URL. The backend runs separately
from `E:\PBL6\backend` and exposes the API at `http://127.0.0.1:8000`.

## Build

```powershell
npm run build
npm run preview
```

The frontend package manifest and lockfile are intentionally scoped to this
directory. Python dependencies are managed by `backend/pyproject.toml`,
`backend/uv.lock` and `uv` — run `cd backend; uv sync` once before starting the
backend.
