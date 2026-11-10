"""In-memory case store (Phase 1 skeleton persistence; DB tables via Alembic)."""

from typing import Any

import time
import uuid

STORE: dict[str, dict[str, Any]] = {"cases": {}, "runs": {}, "events": {}, "idempotency": {}}


def create_submission_stub(payload: dict[str, Any], idem_key: str | None = None) -> dict[str, str]:
    if idem_key and idem_key in STORE["idempotency"]:
        existing: Any = STORE["idempotency"][idem_key]
        return {"case_id": str(existing["case_id"]), "run_id": str(existing["run_id"])}
    case_id = uuid.uuid4().hex[:12]
    run_id = uuid.uuid4().hex[:12]
    STORE["cases"][case_id] = dict(payload)
    STORE["runs"][run_id] = {
        "run_id": run_id,
        "case_id": case_id,
        "mode": "FULL",
        "decision": {
            "status": "APPROVED",
            "awaiting": [],
            "tier": "LOW",
            "score": {"total": 0},
            "reason_codes": [],
        },
        "findings": [{"check_id": "NOOP", "outcome": "PASS"}],
        "claims": [],
    }
    STORE["events"][run_id] = [
        {"seq": 1, "type": "run.started", "data": {}},
        {
            "seq": 2,
            "type": "check.completed",
            "data": {"check_id": "NOOP", "findings": [{"outcome": "PASS"}]},
        },
        {
            "seq": 3,
            "type": "decision.made",
            "data": {"status": "APPROVED", "awaiting": [], "tier": "LOW"},
        },
        {"seq": 4, "type": "run.completed", "data": {}},
    ]
    out = {"case_id": case_id, "run_id": run_id}
    if idem_key:
        STORE["idempotency"][idem_key] = dict(out)
    return out


def reset_store() -> float:
    t0 = time.time()
    for k in STORE:
        STORE[k].clear()
    return (time.time() - t0) * 1000


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def save_run(result: dict[str, Any]) -> None:
    run_id = str(result["run_id"])
    case_id = str(result["case_id"])
    decision = _as_dict(result["decision"])
    score = _as_dict(decision.get("score"))
    STORE["runs"][run_id] = {
        "run_id": run_id,
        "case_id": case_id,
        "mode": result.get("mode", "FULL"),
        "decision": decision,
        "findings": result.get("findings", []),
        "claims": result.get("claims", []),
        "audit": result.get("audit", []),
        "vendor_id": result.get("vendor_id"),
    }
    STORE["cases"][case_id] = {
        "case_id": case_id,
        "run_id": run_id,
        "requester": result.get("requester", ""),
        "status": decision.get("status"),
        "tier": decision.get("tier"),
        "score": score.get("total"),
        "reason_codes": decision.get("reason_codes"),
        "vendor_id": result.get("vendor_id"),
    }
    seq_events: list[dict[str, Any]] = []
    seq = 0
    audit = result.get("audit", [])
    for e in audit if isinstance(audit, list) else []:
        item = _as_dict(e)
        seq += 1
        seq_events.append({"seq": seq, "type": item.get("type"), "data": item.get("payload")})
    seq_events.append(
        {"seq": seq + 1, "type": "decision.made", "data": {"status": decision.get("status")}}
    )
    seq_events.append({"seq": seq + 2, "type": "run.completed", "data": {}})
    STORE["events"][run_id] = seq_events
