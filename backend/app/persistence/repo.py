"""Persistence facade: SQLite-backed store (D-4.0).

Same STORE partitions as before (cases, runs, events, idempotency,
callbacks, docs) so call sites are unchanged, plus durable writes of
submission versions, case events, messages, and check-cache rows that the
resubmit/delta/scheduler machinery reads.
"""

from typing import Any

import time
import uuid

from backend.app.persistence import models
from backend.app.persistence.store import SQLiteStore
from backend.app.persistence.store import session

STORE = SQLiteStore()


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
    with session() as s:
        for table in reversed(models.Base.metadata.sorted_tables):
            if table.name == "alembic_version":
                continue
            s.execute(table.delete())
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
        "message": result.get("message", {}),
        "adjudications": result.get("adjudications", []),
    }
    STORE["cases"][case_id] = {
        "case_id": case_id,
        "run_id": run_id,
        "requester": result.get("requester", ""),
        "submission_type": result.get("submission_type", "NEW_VENDOR"),
        "existing_vendor_id": result.get("existing_vendor_id"),
        "status": decision.get("status"),
        "tier": decision.get("tier"),
        "score": score.get("total"),
        "reason_codes": decision.get("reason_codes"),
        "vendor_id": result.get("vendor_id"),
        "current_version": int(result.get("version", 1)),
    }
    seq_events: list[dict[str, Any]] = []
    seq = 0
    audit = result.get("audit", [])
    for e in audit if isinstance(audit, list) else []:
        item = _as_dict(e)
        seq += 1
        seq_events.append({"seq": seq, "type": item.get("type"), "data": item.get("payload")})
    seq_events.append(
        {"seq": seq + 1, "type": "decision.made",
         "data": {"status": decision.get("status")}}
    )
    seq_events.append({"seq": seq + 2, "type": "run.completed", "data": {}})
    STORE["events"][run_id] = seq_events
    files = result.get("files", {})
    STORE.setdefault("docs", {})[run_id] = files
    # durable normalized rows for resubmit/delta/scheduler queries
    _write_submission_version(result)
    _write_case_events(case_id, audit)
    _write_message(case_id, run_id, result.get("message", {}), decision)


def _write_submission_version(result: dict[str, Any]) -> None:
    from backend.app.core.hashing import canonical_json
    from backend.app.core.hashing import sha256_hex

    payload = _as_dict(result.get("payload", {}))
    version = int(result.get("version", 1))
    with session() as s:
        existing = (
            s.query(models.SubmissionVersion)
            .filter_by(case_id=str(result["case_id"]), version=version)
            .first()
        )
        if existing is None:
            s.add(models.SubmissionVersion(
                case_id=str(result["case_id"]), version=version, payload=payload,
                payload_hash=sha256_hex(canonical_json(payload)),
                created_by=str(result.get("requester", "system"))))


def _write_case_events(case_id: str, audit: Any) -> None:
    with session() as s:
        for e in audit if isinstance(audit, list) else []:
            item = _as_dict(e)
            s.add(models.CaseEvent(
                case_id=case_id, seq=int(item.get("seq", 0)),
                actor=str(item.get("actor", "system")), type=str(item.get("type", "")),
                payload=_as_dict(item.get("payload")),
                prev_hash=str(item.get("prev_hash", "GENESIS")),
                entry_hash=str(item.get("entry_hash", ""))))


def _write_message(case_id: str, run_id: str, message: Any, decision: dict[str, Any]) -> None:
    msg = _as_dict(message)
    if not msg:
        return
    status = str(decision.get("status", "PENDING"))
    kind = {"APPROVED": "APPROVED", "REJECTED": "REJECTED"}.get(status, "PENDING")
    with session() as s:
        s.add(models.Message(
            case_id=case_id, run_id=run_id, audience="VENDOR", kind=kind,
            subject=str(msg.get("subject", ""))[:512],
            body=str(msg.get("body", ""))[:8192],
            items={"items": msg.get("items", [])}))
