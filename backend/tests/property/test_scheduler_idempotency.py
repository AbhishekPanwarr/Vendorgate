from datetime import timedelta

from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from backend.app.core.virtual_clock import get_virtual_now
from backend.app.scheduler.jobs import _nudge_days
from backend.app.scheduler.jobs import nudge_job


def _mk_case(client, payload):
    import json

    return client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(payload)}
    ).json()["case_id"]


def test_advance_split_equals_bulk():
    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    import json

    client = TestClient(create_app())
    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        payload = json.load(fh)["payload"]
    cid = _mk_case(client, payload)
    base = get_virtual_now()
    # bulk: one 10-day jump
    bulk = nudge_job(base + timedelta(days=10))
    bulk_days = sorted(n["nudge_day"] for n in bulk if n["case_id"] == cid)
    assert bulk_days == [1, 3, 7, 10]


@settings(deadline=None)
@given(st.integers(min_value=1, max_value=14))
def test_nudge_prefix_property(days):
    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    import json

    client = TestClient(create_app())
    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        payload = json.load(fh)["payload"]
    cid = _mk_case(client, payload)
    fired = nudge_job(get_virtual_now() + timedelta(days=days))
    got = sorted(n["nudge_day"] for n in fired if n["case_id"] == cid)
    assert got == [d for d in _nudge_days() if d <= days]
