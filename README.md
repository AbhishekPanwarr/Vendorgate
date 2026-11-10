# VendorGate

Evidence-first vendor onboarding (PS-2). Phase 0: frozen contracts + walking skeleton.

## Quickstart

```bash
cp .env.example .env
pip install -e ".[dev]"
alembic upgrade head
uvicorn backend.app.main:app --port 8000
```

Frontend: `npm --prefix frontend install && npm --prefix frontend run dev`.

## Architecture

FastAPI skeleton + NullOrchestrator; frozen contracts in
`backend/app/domain`, `backend/app/core`, `backend/app/pipeline`,
`backend/app/decision`, `backend/app/adapters`. See `docs/process_map.md`,
`docs/assumptions.md`, `docs/adr/`, `docs/decisions.md`.

## Demo

`/` submit → `/runs/{id}` live SSE → `/admin` reset. Deploy: Render
(`render.yaml`); local fallback `docker run -e LLM_MODE=replay -p 8000:8000 <image>`.
