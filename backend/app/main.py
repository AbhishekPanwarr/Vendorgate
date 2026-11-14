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
    async def resubmit(
        case_id: str,
        request: Request,  # noqa: ANN201
        idempotency_key: str | None = Header(default=None),
        if_match: str | None = Header(default=None, alias="If-Match"),
    ):
        from backend.app.core.hashing import canonical_json
        from backend.app.core.hashing import sha256_hex
        from backend.app.persistence.store import append_case_event

        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        if case.get("status") != "PENDING":
            return JSONResponse(
                status_code=403, content={"type": "NOT_RESUBMITTABLE", "status": case.get("status")}
            )
        current = int(case.get("current_version", 1))
        if idempotency_key and idempotency_key in repo.STORE["idempotency"]:
            return JSONResponse(
                status_code=202,
                content=repo.STORE["idempotency"][idempotency_key],
                headers={"Idempotent-Replayed": "true"},
            )
        if if_match is not None and if_match != str(current):
            return JSONResponse(
                status_code=412, content={"type": "VERSION_MISMATCH", "current_version": current}
            )
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

            row = s.query(_m.SubmissionVersion).filter_by(case_id=case_id, version=current).first()
            cur_hash = row.payload_hash if row else ""
        if new_hash == cur_hash:
            return JSONResponse(
                status_code=409, content={"type": "NO_CHANGES", "current_version": current}
            )
        files: dict[str, tuple[str, bytes]] = {}
        for key, item in form.items():
            if key.startswith("file:") and hasattr(item, "read"):
                data = await item.read()
                files[key[5:]] = (item.filename or key[5:], bytes(data))
        from backend.app.pipeline.pipeline import run_delta

        prev_run = repo.STORE["runs"].get(case.get("run_id", ""), {})
        result = await run_delta(
            prev_run.get("payload", {}),
            prev_run.get("findings", []),
            payload,
            files=files or None,
            version=current + 1,
            case_id=case_id,
        )
        for code in result["decision"].get("reason_codes", []):
            append_case_event(
                case_id, "attempt.recorded", {"reason_code": code, "version": current + 1}
            )
        out = {"case_id": case_id, "run_id": result["run_id"], "new_version": current + 1}
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

    @app.get("/api/v1/cases/{case_id}/events")
    def get_case_events(case_id: str):  # noqa: ANN201
        from backend.app.persistence.store import case_events

        if not repo.STORE["cases"].get(case_id):
            return JSONResponse(status_code=404, content={"type": "not-found"})
        return case_events(case_id)

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

    @app.post("/api/v1/cases/{case_id}/appeal", status_code=202)
    async def appeal(case_id: str, request: Request):  # noqa: ANN201
        from backend.app.decision.routing import check_appeal_sod
        from backend.app.persistence.store import append_case_event
        from backend.app.persistence.store import case_events
        from backend.app.persistence.store import session as _session

        case = repo.STORE["cases"].get(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"type": "not-found"})
        if case.get("status") != "REJECTED":
            return JSONResponse(
                status_code=403, content={"type": "NOT_APPEALABLE", "status": case.get("status")}
            )
        body = await request.json()
        actor = request.headers.get("X-Actor", body.get("actor", ""))
        prior = [
            e["actor"]
            for e in case_events(case_id)
            if e["actor"] and e["type"] in ("submission.received", "approval.recorded")
        ]
        prior.append(case.get("requester", ""))
        if not check_appeal_sod(case.get("requester", ""), prior, actor):
            return JSONResponse(
                status_code=403, content={"type": "SEGREGATION_OF_DUTIES_VIOLATION"}
            )
        append_case_event(
            case_id,
            "appeal.received",
            {"reason": body.get("reason", ""), "reviewer": actor},
            actor=actor,
        )
        with _session() as s:
            from backend.app.persistence import models as _m

            row = s.get(_m.Case, case_id)
            if row is not None:
                row.status = "PENDING"
        return {"case_id": case_id, "status": "PENDING", "awaiting": ["INTERNAL"]}

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
        from backend.app.persistence.store import case_events

        out = []
        for c in repo.STORE["cases"].values():
            run = repo.STORE["runs"].get(c.get("run_id", ""), {})
            route = (run.get("decision", {}) or {}).get("approval_route", [])
            appealed = any(e["type"] == "appeal.received" for e in case_events(c["case_id"]))
            if not role or role in route or (role == "COMPLIANCE" and appealed):
                out.append({**c, "approval_route": route, "appealed": appealed})
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

    @app.get("/api/v1/eval/latest")
    def eval_latest():  # noqa: ANN202
        import json as _json

        out = {}
        for name in (
            "latest.json",
            "sets.json",
            "ablation-dev.json",
            "ablation-llm-only-test25.json",
        ):
            _p = Path("eval/reports") / name
            if _p.exists():
                out[name] = _json.loads(_p.read_text())
        return out

    @app.get("/api/v1/policy")
    def get_policy():  # noqa: ANN202
        import hashlib as _hl

        import yaml as _yaml

        base = Path("policy/base.yaml").read_bytes()
        assumptions = (
            _yaml.safe_load(Path("policy/assumptions.yaml").read_text())
            if Path("policy/assumptions.yaml").exists()
            else []
        )
        return {"assumptions": assumptions, "policy_hash": _hl.sha256(base).hexdigest()}

    @app.get("/api/v1/foolit/operators")
    def foolit_operators():  # noqa: ANN202
        import yaml as _yaml

        cat = _yaml.safe_load(Path("datagen/mutations/catalog.yaml").read_text())
        return [
            {
                "id": o["id"],
                "name": o["name"],
                "description": o.get("description", o["name"]),
                "expected": o["expected"],
            }
            for o in cat["operators"]
        ]

    @app.post("/api/v1/foolit/run")
    async def foolit_run(request: Request):  # noqa: ANN201
        import asyncio as _asyncio
        import json as _json
        import random as _random

        body = await request.json()
        vendor_id = str(body.get("vendor_id", ""))
        op_ids = [str(o) for o in body.get("ops", [])]
        world = _json.loads(Path("datagen/out/world.json").read_text())
        vendor = next((v for v in world["vendors"] if v["vendor_id"] == vendor_id), None)
        payload = None
        if vendor is None:
            bases = {
                "HP-1": "hp-1",
                "HP-2": None,
                "HP-3": "hp-3",
                "HP-3-HIGH": "hp-3-high",
                "EC-1": "ec-1-run-1",
                "EC-3a": "ec-3a",
                "EC-3b": "ec-3b",
                "EC-4a": "ec-4a",
                "EC-4b": "ec-4b",
            }
            key = bases.get(vendor_id)
            if key is None and vendor_id == "HP-2":
                payload = _json.loads(Path("backend/tests/fixtures/hp2_payload.json").read_text())
            elif key is not None:
                payload = _json.loads(
                    Path(f"backend/tests/golden/fixtures/{key}.json").read_text()
                )["payload"]
            if payload is None:
                return JSONResponse(status_code=404, content={"type": "unknown-vendor"})
            vendor = {
                "vendor_id": vendor_id,
                "country": payload["company"]["country"],
                "legal_name": payload["company"]["legal_name"],
                "tax": {"tax_id": payload["tax"]["tax_id"]},
                "bank": payload["bank"],
                "truth": {"incorporation_year": 2020},
            }
        from datagen.build_dataset import _ctx, _l3_entries, _merge_files, _truth_mocks
        from datagen.mutations.apply import OPS
        from eval.case_runner import run_case

        rng = _random.Random(0)
        ctx = _ctx()
        from datagen.submissions import submission_for

        if payload is None and vendor is not None:
            payload = submission_for(vendor)
        for op_id in op_ids:
            if op_id not in OPS:
                return JSONResponse(
                    status_code=400, content={"type": "unknown-operator", "op": op_id}
                )
            OPS[op_id](payload, vendor, world, rng, ctx, None)
        _truth_mocks(ctx, vendor, payload)
        files, l1, deg = _merge_files(ctx, payload, op_ids, rng)
        import yaml as _yaml

        catalog = {
            o["id"]: o
            for o in _yaml.safe_load(Path("datagen/mutations/catalog.yaml").read_text())[
                "operators"
            ]
        }
        order = {"APPROVED": 0, "PENDING": 1, "REJECTED": 2}
        exps = [catalog[o]["expected"] for o in op_ids]
        worse = max(exps, key=lambda e: order[e["status"]]) if exps else None
        case = {
            "op": op_ids,
            "vendor_id": vendor_id,
            "payload": payload,
            "expected": {
                "status": worse["status"] if worse else "APPROVED",
                "awaiting": sorted({a for e in exps for a in e["awaiting"]}),
                "blocking_reason_codes": sorted(
                    {c for e in exps for c in e["blocking_reason_codes"]}
                ),
                "critical": any(e["critical"] for e in exps),
            }
            if exps
            else {
                "status": "APPROVED",
                "awaiting": [],
                "blocking_reason_codes": [],
                "critical": False,
            },
            "mocks": {f"{a}|{k}": v for (a, k), v in ctx["mocks"].items()},
            "master": ctx["master"],
            "sanctions": ctx["sanctions"],
            "pep": ctx["pep"],
            "adverse": ctx["adverse"],
            "faults": ctx["faults"],
            "setup_cases": ctx["setup_cases"],
            "l3": _l3_entries(payload),
            "files": files,
            "l1_rendered": l1,
            "degraded": deg,
        }
        pack = await _asyncio.to_thread(run_case, case)
        dec = pack["decision"]
        actual = {
            "status": dec["status"],
            "awaiting": dec.get("awaiting", []),
            "reason_codes": dec.get("reason_codes", []),
        }
        attempt = {
            "vendor_id": vendor_id,
            "ops": op_ids,
            "expected": case["expected"],
            "actual": actual,
            "source": "redteam",
        }
        with open("eval/reports/redteam.jsonl", "a") as _fh:
            _fh.write(_json.dumps(attempt) + "\n")
        return {
            "expected": case["expected"],
            "actual": actual,
            "match": (case["expected"]["status"] == actual["status"]),
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

    @app.post("/api/v1/admin/clock/advance")
    async def clock_advance(request: Request):  # noqa: ANN201
        from backend.app.core.virtual_clock import advance_virtual_now
        from backend.app.scheduler.jobs import run_scheduler

        try:
            body = await request.json()
            days = int(body.get("days", 0))
            now = advance_virtual_now(days)
        except ValueError:
            return JSONResponse(status_code=400, content={"type": "bad-days"})
        jobs = run_scheduler(now)
        return {"now": now.isoformat(), "jobs_fired": jobs}

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
