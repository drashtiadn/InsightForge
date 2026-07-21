# InsightForge

Autonomous Multi-Agent Research System. Currently a single Python (FastAPI) backend service that exposes a `/health` endpoint; there is no frontend, database, or agent/LLM logic yet.

## Cursor Cloud specific instructions

### Services

- Backend API (FastAPI + Uvicorn). This is the only service. Source lives in `backend/app`, entrypoint `app.main:app`.

### Running the backend (dev)

- The update script creates a virtualenv at `.venv` (repo root) and installs `requirements.txt` into it. Activate it before running anything: `source /workspace/.venv/bin/activate`.
- Uvicorn must be launched from the `backend/` directory because imports use the `app.` package prefix:
  `cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Serves on port 8000. Swagger UI at `/docs`, health check at `/health`.

### Config

- Settings are loaded via pydantic-settings from `.env` at the repo root (NOT `backend/.env`) — see `backend/app/core/config.py`. All settings have defaults, so the app runs without a `.env`. Copy `.env.example` -> `.env` at the repo root to customize.

### Lint / Test / Build

- No lint, test, or build tooling is configured in this repo (no pytest, ruff/black, mypy, Makefile, or CI). There is no build step (pure Python). `python -m compileall backend/app` can be used as a basic syntax check.
