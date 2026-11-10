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
        if idempotency_key and idempotency_key in repo.STORE["idempotency"]:
            return repo.STORE["idempotency"][idempotency_key]
        from backend.app.pipeline.pipeline import run_full

        result = await run_full(payload)
        out = {"case_id": result["case_id"], "run_id": result["run_id"]}
        if idempotency_key:
            repo.STORE["idempotency"][idempotency_key] = out
        return out

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

    @app.get("/api/v1/cases")
    def list_cases():  # noqa: ANN202
        return list(repo.STORE["cases"].values())

    @app.get("/api/v1/cases/{case_id}")
    def get_case(case_id: str):  # noqa: ANN201
        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        run = repo.STORE["runs"].get(case["run_id"], {})
        return {**case, "run": run}

    @app.get("/api/v1/cases/{case_id}/audit")
    def get_audit(case_id: str):  # noqa: ANN201
        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        run = repo.STORE["runs"].get(case["run_id"], {})
        return run.get("audit", [])

    @app.get("/api/v1/cases/{case_id}/audit/verify")
    def verify_audit(case_id: str):  # noqa: ANN201
        from backend.app.persistence.audit_chain import verify_chain

        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        run = repo.STORE["runs"].get(case["run_id"], {})
        return verify_chain(run.get("audit", []))

    @app.post("/api/v1/cases/{case_id}/resolutions")
    async def add_resolution(case_id: str, request: Request):  # noqa: ANN201
        from backend.app.decision.routing import resolve_allowed

        from backend.app.core.policy import load_policy

        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        body = await request.json()
        role = request.headers.get("X-Role", "")
        if not resolve_allowed(body.get("reason_code", ""), role, load_policy("policy")):
            return JSONResponse(status_code=403, content={"type": "role-not-allowed"})
        return {"ok": True, "note": "resolutions take effect in Phase 2 runs"}

    @app.post("/api/v1/cases/{case_id}/approvals")
    async def add_approval(case_id: str, request: Request):  # noqa: ANN201
        from backend.app.decision.routing import check_sod

        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        actor = request.headers.get("X-Actor", "")
        role = request.headers.get("X-Role", "")
        requester = case.get("requester") or actor
        if not check_sod(requester, actor, role):
            return JSONResponse(
                status_code=403, content={"type": "SEGREGATION_OF_DUTIES_VIOLATION"}
            )
        return {"ok": True, "case_id": case_id, "actor": actor, "role": role}

    @app.post("/api/v1/cases/{case_id}/callback")
    def record_callback(case_id: str):  # noqa: ANN201, ANN001
        return JSONResponse(status_code=422, content={"type": "no-callback-required"})

    @app.get("/api/v1/vendors")
    def list_vendors():  # noqa: ANN202
        return [c for c in repo.STORE["cases"].values() if c.get("vendor_id")]

    @app.get("/api/v1/metrics/dashboard")
    def dashboard_metrics():  # noqa: ANN202
        cases = list(repo.STORE["cases"].values())
        by_status: dict[str, int] = {}
        for c in cases:
            by_status[c.get("status", "?")] = by_status.get(c.get("status", "?"), 0) + 1
        auto = sum(1 for c in cases if c.get("status") == "APPROVED")
        return {
            "volume": len(cases),
            "by_status": by_status,
            "auto_approve_rate": (auto / len(cases)) if cases else 0.0,
        }

    @app.post("/api/v1/admin/reset")
    def admin_reset():  # noqa: ANN202
        ms = repo.reset_store()
        return {"ok": True, "duration_ms": ms}

    dist = Path("frontend/dist")
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):  # noqa: ANN201, ANN001
            from fastapi.responses import FileResponse

            if path.startswith("api/"):
                return JSONResponse(status_code=404, content={"type": "not-found"})
            return FileResponse(str(dist / "index.html"))

    return app


app = create_app()
