"""Scheduler: nudge + deadline jobs, idempotent via case_events."""

from datetime import datetime
from typing import Any

from backend.app.core.policy import load_policy
from backend.app.persistence import models
from backend.app.persistence.store import append_case_event
from backend.app.persistence.store import case_events
from backend.app.persistence.store import session


def _days_since(opened_at: Any, now: datetime) -> int:
    if isinstance(opened_at, str):
        opened_at = datetime.fromisoformat(opened_at)
    opened_day = opened_at.date() if hasattr(opened_at, "date") else opened_at
    now_day = now.date() if hasattr(now, "date") else now
    delta = now_day - opened_day
    days: int = delta.days
    return max(0, days)


def _nudge_days() -> list[int]:
    raw: Any = load_policy("policy").raw["base"]["lifecycle"].get("nudge_days", [1, 3, 7, 10])
    return [int(str(d)) for d in raw]


def _due_days() -> int:
    val: Any = load_policy("policy").raw["base"]["lifecycle"].get("due_days", 14)
    return int(str(val))


def _sent_nudge_days(case_id: str) -> set[int]:
    return {int(e["payload"].get("nudge_day", -1)) for e in case_events(case_id, "nudge.sent")}


def nudge_job(now: datetime) -> list[dict[str, Any]]:
    from backend.app.comms.messages import check_message

    fired = []
    with session() as s:
        cases = s.query(models.Case).filter_by(status="PENDING").all()
        rows: list[dict[str, Any]] = [{"id": c.id, "opened_at": c.opened_at} for c in cases]
    for c in rows:
        elapsed = _days_since(c["opened_at"], now)
        sent = _sent_nudge_days(c["id"])
        open_items = _open_vendor_items(c["id"])
        if not open_items:
            continue
        for day in _nudge_days():
            if day <= elapsed and day not in sent:
                body = render_nudge(c["id"], open_items)
                errs = check_message(
                    "nudge",
                    body,
                    [{"fix_code": it["fix_code"]} for it in open_items],
                    status="PENDING",
                )
                if errs:
                    continue
                append_case_event(
                    c["id"],
                    "nudge.sent",
                    {
                        "nudge_day": day,
                        "items": [it["fix_code"] for it in open_items],
                        "body": body,
                    },
                )
                fired.append({"case_id": c["id"], "nudge_day": day})
    return fired


def _open_vendor_items(case_id: str) -> list[dict[str, Any]]:
    from backend.app.persistence import repo

    case = repo.STORE["cases"].get(case_id, {})
    run = repo.STORE["runs"].get(case.get("run_id", ""), {})
    items = []
    for f in run.get("findings", []):
        if f.get("outcome") == "FAIL" and f.get("fixed_by") == "VENDOR" and f.get("fix"):
            items.append(
                {"fix_code": f["fix"].get("code", f["check_id"]), "title": f.get("title", "")}
            )
    return items


def render_nudge(case_id: str, open_items: list[dict[str, Any]]) -> str:
    lines = [
        "Hi, a reminder: the following items are still needed:",
        *[f"{i}. [[{it['fix_code']}]] {it['title']}" for i, it in enumerate(open_items, 1)],
        "Please resubmit at your earliest convenience. [Resubmit → /resubmit]",
    ]
    return "\n".join(lines)


def deadline_job(now: datetime) -> list[dict[str, Any]]:
    fired = []
    with session() as s:
        cases = s.query(models.Case).filter_by(status="PENDING").all()
        rows: list[dict[str, Any]] = [{"id": c.id, "opened_at": c.opened_at} for c in cases]
    due = _due_days()
    for c in rows:
        if _days_since(c["opened_at"], now) <= due:
            continue
        if any(e["type"] == "case.closed" for e in case_events(c["id"])):
            continue
        append_case_event(
            c["id"], "case.closed", {"reason": "ABANDONED", "detail": "deadline passed"}
        )
        with session() as s:
            row = s.get(models.Case, c["id"])
            if row is not None and row.status == "PENDING":
                row.status = "REJECTED"
                row.closed_at = now
        fired.append({"case_id": c["id"], "reason": "ABANDONED"})
    return fired


def run_scheduler(now: datetime) -> dict[str, Any]:
    nudges = nudge_job(now)
    closed = deadline_job(now)
    return {"nudges": nudges, "closed": closed}
