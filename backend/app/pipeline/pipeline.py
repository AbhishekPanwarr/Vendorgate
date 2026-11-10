"""Full pipeline runner: S0 claims -> checks -> score -> decide -> audit/activate."""

import uuid
from typing import Any

from backend.app.core.clock import Clock
from backend.app.core.clock import RealClock
from backend.app.core.policy import Policy
from backend.app.core.policy import load_policy
from backend.app.decision.engine import decide
from backend.app.domain.enums import RunMode
from backend.app.domain.enums import Status
from backend.app.domain.submission import VendorSubmission
from backend.app.persistence import repo
from backend.app.persistence.audit_chain import GENESIS
from backend.app.persistence.audit_chain import append_event
from backend.app.pipeline.checks import bank as _bank  # noqa: F401  (register checks)
from backend.app.pipeline.checks import doc as _doc  # noqa: F401
from backend.app.pipeline.checks import dup as _dup  # noqa: F401
from backend.app.pipeline.checks import geo as _geo  # noqa: F401
from backend.app.pipeline.checks import name as _name  # noqa: F401
from backend.app.pipeline.checks import req as _req  # noqa: F401
from backend.app.pipeline.checks import san as _san  # noqa: F401
from backend.app.pipeline.checks import tax as _tax  # noqa: F401
from backend.app.pipeline.checks import ver as _ver  # noqa: F401
from backend.app.pipeline.context import RunContext
from backend.app.pipeline.orchestrator import DagOrchestrator
from backend.app.pipeline.stages.s0_intake import build_claims


def _load_policy() -> Policy:
    return load_policy("policy")


def _now_iso(clock: Clock) -> str:
    return clock.now().isoformat()


def _sanctions_version() -> str:
    import hashlib as _hl
    from pathlib import Path as _Path

    h = _hl.sha256()
    for name in ("sanctions_mock.jsonl", "pep_mock.jsonl", "adverse_mock.jsonl"):
        p = _Path("backend/app/screening/lists") / name
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _map_freshness(rep: dict[str, Any], dtype: str, fields: dict[str, Any]) -> None:
    def _val(name: str) -> str:
        f = fields.get(name, {})
        return str(f.get("value") or "") if isinstance(f, dict) else ""

    fr = rep.setdefault("freshness", {})
    if dtype == "W9":
        fr["signed"] = bool(_val("signature_present")) and bool(_val("signature_date"))
    if dtype == "COI":
        for fname, f in fields.items():
            if isinstance(f, dict) and "expiry" in fname.lower() and f.get("value"):
                fr["coi_expiry"] = f["value"]
    if dtype in ("BANK_LETTER", "VOIDED_CHEQUE"):
        for fname, f in fields.items():
            if isinstance(f, dict) and "date" in fname.lower() and f.get("value"):
                fr["bank_letter_date"] = f["value"]
                break


async def run_full(
    payload: dict[str, Any],
    clock: Clock | None = None,
    files: dict[str, tuple[str, bytes]] | None = None,
    llm: Any = None,
    version: int = 1,
    case_id: str | None = None,
) -> dict[str, Any]:
    from backend.app.llm.factory import llm_model
    from backend.app.llm.factory import make_llm
    from backend.app.network.graph import seed_master
    from backend.app.persistence.cache import DbCheckCache
    from backend.app.pipeline.stages.s1_docs import ingest_document

    seed_master()
    submission = VendorSubmission.model_validate(payload)
    policy = _load_policy()
    clock = clock or RealClock()
    case_id = case_id or uuid.uuid4().hex[:12]
    run_id = uuid.uuid4().hex[:12]
    events: list[dict[str, Any]] = []

    def emit(e: dict[str, Any]) -> None:
        events.append(e)

    ctx = RunContext(
        case_id=case_id,
        run_id=run_id,
        submission=submission,
        policy=policy,
        adapters={},
        llm=llm or make_llm(),
        clock=clock,
        cache=DbCheckCache(),
        emit=emit,
    )
    for claim in build_claims(submission):
        ctx.add_claim(claim)

    # S1: ingest declared documents with attached file bytes
    from backend.app.domain.enums import Source
    from backend.app.llm.tasks_extract import grounding_ok
    from backend.app.llm.tasks_l1 import extract_doc
    from backend.app.pipeline.stages.s0_intake import _claim as _mkclaim

    ctx.doc_reports = {}
    declared_by_id = {d.doc_id: d.doc_type.value for d in submission.documents}
    import hashlib as _hl

    _h = _hl.sha256()
    for _did in sorted((files or {}).keys()):
        _h.update(_did.encode())
        _h.update((files or {})[_did][1])
    ctx.add_claim(_mkclaim("docs.content_hash", _h.hexdigest(), _h.hexdigest()))
    _dig = ";".join(
        sorted(f"{d.doc_id}:{d.doc_type.value}" for d in submission.documents))
    ctx.add_claim(_mkclaim("documents.digest", _dig, _dig))
    ctx.add_claim(_mkclaim("clock.today", clock.now().date().isoformat(),
                           clock.now().date().isoformat()))
    ctx.add_claim(_mkclaim("lists.sanctions_version", _sanctions_version(),
                           _sanctions_version()))
    for doc_id, (filename, data) in (files or {}).items():
        rep = ingest_document(
            doc_id, declared_by_id.get(doc_id, "UNKNOWN"), filename, data, clock.now().date()
        )
        if rep.get("upload_ok") and rep.get("text_pages"):
            dtype = rep["detected_type"] if rep["detect_confident"] else rep["declared"]
            try:
                out = await extract_doc(ctx.llm, llm_model(), dtype, rep["text_pages"])
                fields = out.model_dump()
                text = "\n".join(rep["text_pages"])
                for fname, f in fields.items():
                    if not isinstance(f, dict):
                        continue
                    if not grounding_ok(f.get("value"), f.get("quote"), text):
                        rep.setdefault("ungrounded", []).append(fname)
                        continue
                    if f.get("value") is not None:
                        claim = _mkclaim(f"doc:{doc_id}.{fname}", f.get("value"), f.get("value"))
                        claim.source = Source.DOC
                        claim.doc_id = doc_id
                        claim.page = f.get("page")
                        claim.quote = (f.get("quote") or "")[:200]
                        claim.confidence = float(f.get("confidence") or 0)
                        ctx.add_claim(claim)
                _map_freshness(rep, dtype, fields)
            except Exception:
                rep.setdefault("ungrounded", []).append("*l1-unavailable*")
        for claim in rep.get("claims", []):
            ctx.add_claim(claim)
        ctx.doc_reports[doc_id] = rep

    await DagOrchestrator().run(ctx, RunMode.FULL)
    from backend.app.comms.messages import compose as compose_message
    from backend.app.pipeline.stages.s8 import run_s8

    adjudications = await run_s8(ctx)
    decision = decide(findings=ctx.findings, resolutions=[], submission_facts=ctx, policy=policy)
    message = compose_message(
        {"status": decision.status.value, "reason_codes": decision.reason_codes},
        [f.model_dump(mode="json") for f in ctx.findings],
        submission.company.legal_name,
        due="in 14 days",
    )

    # audit chain
    prev = GENESIS
    seq = 0
    audit: list[dict[str, Any]] = []

    def log(type: str, payload_e: dict[str, Any], actor: str = "system") -> None:
        nonlocal prev, seq
        seq += 1
        e = append_event(case_id, seq, _now_iso(clock), actor, type, payload_e, prev)
        prev = str(e["entry_hash"])
        audit.append(e)

    log("submission.received", {"version": version})
    log("run.started", {"run_id": run_id})
    for f in ctx.findings:
        log(
            "finding.recorded",
            {"check_id": f.check_id, "outcome": f.outcome.value, "reason_code": f.reason_code},
        )
    log(
        "decision.made",
        {
            "status": decision.status.value,
            "tier": decision.tier.value,
            "score": decision.score.total,
        },
    )
    log("message.queued", {"subject": message["subject"]})

    vendor_id = None
    if decision.status == Status.APPROVED:
        vendor_id = "V-" + case_id[:6].upper()
        log("vendor.activated", {"vendor_id": vendor_id})

    result = {
        "run_id": run_id,
        "case_id": case_id,
        "mode": "FULL",
        "version": version,
        "payload": submission.model_dump(mode="json"),
        "requester": submission.requester.name,
        "submission_type": submission.submission_type.value,
        "existing_vendor_id": submission.existing_vendor_id,
        "files": {
            k: [fn, __import__("base64").b64encode(data).decode()]
            for k, (fn, data) in (files or {}).items()
        },
        "decision": decision.model_dump(mode="json"),
        "findings": [f.model_dump(mode="json") for f in ctx.findings],
        "claims": [c.model_dump(mode="json") for c in ctx.claims.values()],
        "audit": audit,
        "vendor_id": vendor_id,
        "message": message,
        "adjudications": adjudications,
        "events": events,
    }
    repo.save_run(result)
    return result
