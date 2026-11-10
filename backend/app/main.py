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

        files: dict[str, tuple[str, bytes]] = {}
        for key, item in form.items():
            if key.startswith("file:") and hasattr(item, "read"):
                data = await item.read()
                files[key[5:]] = (item.filename or key[5:], bytes(data))
        result = await run_full(payload, files=files or None)
        out = {"case_id": result["case_id"], "run_id": result["run_id"]}
        if idempotency_key:
            repo.STORE["idempotency"][idempotency_key] = out
        return out

    @app.post("/api/v1/cases/{case_id}/resubmit", status_code=202)
    async def resubmit(case_id: str, request: Request,  # noqa: ANN201
                       idempotency_key: str | None = Header(default=None),
                       if_match: str | None = Header(default=None, alias="If-Match")):
        from backend.app.core.hashing import canonical_json
        from backend.app.core.hashing import sha256_hex
        from backend.app.persistence.store import append_case_event
        from backend.app.pipeline.pipeline import run_full

        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        if case.get("status") != "PENDING":
            return JSONResponse(status_code=403,
                                content={"type": "NOT_RESUBMITTABLE",
                                         "status": case.get("status")})
        current = int(case.get("current_version", 1))
        if idempotency_key and idempotency_key in repo.STORE["idempotency"]:
            return JSONResponse(
                status_code=202,
                content=repo.STORE["idempotency"][idempotency_key],
                headers={"Idempotent-Replayed": "true"},
            )
        if if_match is not None and if_match != str(current):
            return JSONResponse(status_code=412,
                                content={"type": "VERSION_MISMATCH",
                                         "current_version": current})
        form = await request.form()
        raw = form.get("payload", "{}")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else {}
            sub = VendorSubmission.model_validate(payload)
            payload = sub.model_dump(mode="json")
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"type": "validation-error", "title": "Invalid submission"},
                headers={"content-type": "application/problem+json"},
            )
        new_hash = sha256_hex(canonical_json(payload))
        from backend.app.persistence.store import session as open_db_session

        with open_db_session() as s:
            from backend.app.persistence import models as _m

            row = (s.query(_m.SubmissionVersion)
                   .filter_by(case_id=case_id, version=current).first())
            cur_hash = row.payload_hash if row else ""
        if new_hash == cur_hash:
            return JSONResponse(status_code=409,
                                content={"type": "NO_CHANGES",
                                         "current_version": current})
        files: dict[str, tuple[str, bytes]] = {}
        for key, item in form.items():
            if key.startswith("file:") and hasattr(item, "read"):
                data = await item.read()
                files[key[5:]] = (item.filename or key[5:], bytes(data))
        result = await run_full(payload, files=files or None, version=current + 1,
                                case_id=case_id)
        for code in result["decision"].get("reason_codes", []):
            append_case_event(case_id, "attempt.recorded",
                              {"reason_code": code, "version": current + 1})
        out = {"case_id": case_id, "run_id": result["run_id"],
               "new_version": current + 1}
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
    async def record_callback(case_id: str, request: Request):  # noqa: ANN201
        from backend.app.core.policy import load_policy
        from backend.app.decision.routing import check_callback

        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        body = await request.json()
        if not body.get("attested"):
            return JSONResponse(status_code=422, content={"type": "attestation-required"})
        policy = load_policy("policy")
        min_age = int(policy.raw["base"]["lifecycle"].get("callback_number_min_age_days", 30))
        run = repo.STORE["runs"].get(case["run_id"], {})
        phones = [
            c.get("value", "") for c in run.get("claims", []) if c.get("path", "").endswith("phone")
        ]
        verdict = check_callback(
            str(body.get("number_used", "")),
            str(body.get("number_source", "")),
            [str(p) for p in phones],
            int(body.get("number_age_days", 0)),
            min_age,
            bool(body.get("attested")),
        )
        repo.STORE.setdefault("callbacks", []).append(
            {
                "case_id": case_id,
                "number_used": body.get("number_used"),
                "number_source": body.get("number_source"),
                "outcome": body.get("outcome", ""),
                "independent": verdict["ok"],
                "actor": request.headers.get("X-Actor", ""),
                "attested": True,
            }
        )
        if not verdict["ok"]:
            return {"ok": False, "reason": verdict["reason"]}
        return {
            "ok": True,
            "case_id": case_id,
            "cleared": ["BANK_CHANGE_REQUIRES_CALLBACK", "CALLBACK_REQUIRED"],
        }

    @app.get("/api/v1/vendors")
    def list_vendors():  # noqa: ANN202
        return [c for c in repo.STORE["cases"].values() if c.get("vendor_id")]

    @app.get("/api/v1/cases/{case_id}/docs/{doc_id}")
    def get_doc(case_id: str, doc_id: str):  # noqa: ANN201
        from fastapi.responses import Response

        import base64

        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        run = repo.STORE["runs"].get(case["run_id"], {})
        docs = (repo.STORE.get("docs", {}) or {}).get(run.get("run_id", ""), {})
        _ = run
        entry = docs.get(doc_id)
        if not entry:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        return Response(content=base64.b64decode(entry[1]), media_type="application/pdf")

    @app.get("/api/v1/cases/{case_id}/messages")
    def get_messages(case_id: str):  # noqa: ANN201
        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        run = repo.STORE["runs"].get(case["run_id"], {})
        return run.get("message", {})

    @app.get("/api/v1/approvals")
    def approvals_queue(role: str = ""):  # noqa: ANN201, ANN001
        out = []
        for c in repo.STORE["cases"].values():
            run = repo.STORE["runs"].get(c.get("run_id", ""), {})
            route = (run.get("decision", {}) or {}).get("approval_route", [])
            if not role or role in route:
                out.append({**c, "approval_route": route})
        return out

    @app.post("/api/v1/cases/{case_id}/retry-verification")
    async def retry_verification(case_id: str):  # noqa: ANN201
        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        run = repo.STORE["runs"].get(case["run_id"], {})
        unverifiable = [f for f in run.get("findings", []) if f.get("outcome") == "UNVERIFIABLE"]
        if not unverifiable:
            return {
                "ok": True,
                "retried": 0,
                "status": (run.get("decision", {}) or {}).get("status"),
            }
        return {
            "ok": True,
            "retried": len(unverifiable),
            "note": "clear the adapter fault and resubmit; delta re-run is Phase 4",
        }

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
