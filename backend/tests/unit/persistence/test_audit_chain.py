from backend.app.persistence.audit_chain import append_event
from backend.app.persistence.audit_chain import GENESIS
from backend.app.persistence.audit_chain import verify_chain


def _chain(n=10):
    events, prev = [], GENESIS
    for i in range(1, n + 1):
        e = append_event(
            "c1", i, "2026-01-01T00:00:00+00:00", "system", "finding.recorded", {"i": i}, prev
        )
        prev = e["entry_hash"]
        events.append(e)
    return events


def test_chain_verifies():
    assert verify_chain(_chain())["ok"] is True


def test_tamper_detected():
    events = _chain()
    events[4] = {**events[4], "payload": {"i": 999}}
    r = verify_chain(events)
    assert r["ok"] is False and r["broken_at"] == 5
