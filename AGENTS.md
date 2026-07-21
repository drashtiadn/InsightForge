# InsightForge

Autonomous Multi-Agent Research System. Currently a single Python/FastAPI backend service (`backend/app`).

## Cursor Cloud specific instructions

### Service: backend (FastAPI)
- Python 3.12. Dependencies are installed into a virtualenv at `/workspace/.venv` by the startup update script (`pip install -r requirements.txt`).
- Runtime config is loaded from `/workspace/.env` (see `.env.example`). `.env` is gitignored; copy it from `.env.example` if missing. `backend/app/core/config.py` reads `.env` from the repo root, not from `backend/`.
- Run the dev server from the `backend/` directory so the `app` package resolves:
  `/workspace/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Hot reload watches `/workspace/backend`. Editing files under `backend/app` reloads automatically; new dependencies require restarting the server.
- Endpoints: `GET /health` (liveness), plus FastAPI's `GET /docs` (Swagger UI) and `GET /openapi.json`.

### Lint / test / build
- There is no lint or test tooling configured (no pytest/ruff/flake8/mypy in `requirements.txt`, no config files). A syntax check can be run with `/workspace/.venv/bin/python -m compileall -q backend/app`. There is no separate build step for this Python service.
