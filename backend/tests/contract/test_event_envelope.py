from backend.app.api.events import ALL_EVENT_TYPES
from backend.app.api.events import RunEvent
from backend.app.api.events import from_sse_frame
from backend.app.api.events import to_sse


def test_all_types_present():
    assert len(ALL_EVENT_TYPES) == 13
    assert "decision.made" in ALL_EVENT_TYPES


def test_sse_roundtrip():
    from datetime import datetime
    from datetime import timezone

    e = RunEvent(
        seq=3, ts=datetime.now(timezone.utc), run_id="r", type="check.completed", data={"a": 1}
    )
    frame = to_sse(e)
    assert frame.startswith("id: 3\nevent: check.completed\n")
    back = from_sse_frame(frame)
    assert back.seq == 3 and back.run_id == "r"
