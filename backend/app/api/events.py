"""Event envelope + SSE contract."""

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel

EventType = Literal[
    "run.started",
    "stage.started",
    "stage.completed",
    "check.started",
    "check.completed",
    "risk.updated",
    "llm.call",
    "adjudication.completed",
    "decision.made",
    "message.queued",
    "run.completed",
    "run.failed",
    "dashboard.updated",
]

ALL_EVENT_TYPES: list[str] = [
    "run.started",
    "stage.started",
    "stage.completed",
    "check.started",
    "check.completed",
    "risk.updated",
    "llm.call",
    "adjudication.completed",
    "decision.made",
    "message.queued",
    "run.completed",
    "run.failed",
    "dashboard.updated",
]


class RunEvent(BaseModel):
    seq: int
    ts: datetime
    run_id: str
    type: EventType
    data: dict[str, Any] = {}


def to_sse(event: RunEvent) -> str:
    import json

    return f"id: {event.seq}\nevent: {event.type}\ndata: {json.dumps({'seq': event.seq, 'run_id': event.run_id, 'type': event.type, 'data': event.data})}\n\n"


def from_sse_frame(frame: str) -> RunEvent:
    import json

    lines = dict(line.split(": ", 1) for line in frame.strip().splitlines() if ": " in line)
    payload = json.loads(lines["data"])
    return RunEvent(
        seq=int(lines["id"]),
        ts=datetime.now(),
        run_id=payload["run_id"],
        type=payload["type"],
        data=payload.get("data", {}),
    )
