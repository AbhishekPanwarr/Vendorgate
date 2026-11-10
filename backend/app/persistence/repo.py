"""CaseRepo stub (Phase 0 skeleton)."""

import time
import uuid

STORE: dict = {"cases": {}, "runs": {}, "events": {}, "idempotency": {}}


def create_submission_stub(payload: dict, idem_key: str | None = None):
    if idem_key and idem_key in STORE["idempotency"]:
        return STORE["idempotency"][idem_key]
    case_id = uuid.uuid4().hex[:12]
    run_id = uuid.uuid4().hex[:12]
    STORE["cases"][case_id] = payload
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
        STORE["idempotency"][idem_key] = out
    return out


def reset_store() -> float:
    t0 = time.time()
    for k in STORE:
        STORE[k].clear()
    return (time.time() - t0) * 1000
