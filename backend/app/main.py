"""FastAPI app factory + skeleton routes."""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi import Header
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.app.domain.submission import VendorSubmission
from backend.app.persistence import repo


def create_app() -> FastAPI:
    app = FastAPI(title="VendorGate")

    @app.get("/healthz")
    def healthz():  # noqa: ANN202
        return {"ok": True}

    @app.get("/readyz")
    def readyz():  # noqa: ANN202
        try:
            from backend.app.core.policy import load_policy

            load_policy("policy")
        except Exception as e:
            return JSONResponse(status_code=503, content={"reason": "policy", "detail": str(e)})
        return {"ok": True}

    @app.get("/api/v1/schema/submission")
    def schema():  # noqa: ANN202
        return VendorSubmission.model_json_schema()

    @app.post("/api/v1/submissions", status_code=202)
    async def submissions(request: Request, idempotency_key: str | None = Header(default=None)):  # noqa: ANN201
        form = await request.form()
        raw = form.get("payload", "{}")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else {}
            VendorSubmission.model_validate(payload)
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"type": "validation-error", "title": "Invalid submission"},
                headers={"content-type": "application/problem+json"},
            )
        return repo.create_submission_stub(payload, idem_key=idempotency_key)

    @app.get("/api/v1/runs/{run_id}")
    def get_run(run_id: str):  # noqa: ANN201
        if run_id not in repo.STORE["runs"]:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        return repo.STORE["runs"][run_id]

    @app.get("/api/v1/runs/{run_id}/events")
    def run_events(run_id: str, last_event_id: str | None = Header(default=None)):  # noqa: ANN201
        events = repo.STORE["events"].get(run_id, [])
        start = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0

        def gen():  # noqa: ANN202
            yield ": hb\n\n"
            for e in events:
                if e["seq"] > start:
                    yield f"id: {e['seq']}\nevent: {e['type']}\ndata: {json.dumps(e)}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.post("/api/v1/admin/reset")
    def admin_reset():  # noqa: ANN202
        ms = repo.reset_store()
        return {"ok": True, "duration_ms": ms}

    dist = Path("frontend/dist")
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="spa")

    return app


app = create_app()
