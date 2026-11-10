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
from backend.app.pipeline.checks import geo as _geo  # noqa: F401
from backend.app.pipeline.checks import name as _name  # noqa: F401
from backend.app.pipeline.checks import req as _req  # noqa: F401
from backend.app.pipeline.checks import tax as _tax  # noqa: F401
from backend.app.pipeline.context import CheckCache
from backend.app.pipeline.context import RunContext
from backend.app.pipeline.orchestrator import DagOrchestrator
from backend.app.pipeline.stages.s0_intake import build_claims


def _load_policy() -> Policy:
    return load_policy("policy")


def _now_iso(clock: Clock) -> str:
    return clock.now().isoformat()


async def run_full(payload: dict[str, Any], clock: Clock | None = None) -> dict[str, Any]:
    submission = VendorSubmission.model_validate(payload)
    policy = _load_policy()
    clock = clock or RealClock()
    case_id = uuid.uuid4().hex[:12]
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
        llm=None,
        clock=clock,
        cache=CheckCache(),
        emit=emit,
    )
    for claim in build_claims(submission):
        ctx.add_claim(claim)

    await DagOrchestrator().run(ctx, RunMode.FULL)
    decision = decide(findings=ctx.findings, resolutions=[], submission_facts=ctx, policy=policy)

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

    log("submission.received", {"version": 1})
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

    vendor_id = None
    if decision.status == Status.APPROVED:
        vendor_id = "V-" + case_id[:6].upper()
        log("vendor.activated", {"vendor_id": vendor_id})

    result = {
        "run_id": run_id,
        "case_id": case_id,
        "mode": "FULL",
        "requester": submission.requester.name,
        "decision": decision.model_dump(mode="json"),
        "findings": [f.model_dump(mode="json") for f in ctx.findings],
        "claims": [c.model_dump(mode="json") for c in ctx.claims.values()],
        "audit": audit,
        "vendor_id": vendor_id,
        "events": events,
    }
    repo.save_run(result)
    return result
