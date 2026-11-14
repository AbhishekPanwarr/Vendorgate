from fastapi.testclient import TestClient

from backend.app.main import create_app

client = TestClient(create_app())


def test_advance_validation():
    r = client.post("/api/v1/admin/clock/advance", json={"days": 0})
    assert r.status_code == 400
    r = client.post("/api/v1/admin/clock/advance", json={"days": -3})
    assert r.status_code == 400


def test_nudge_idempotency():
    import json
    from datetime import timedelta

    from backend.app.core.virtual_clock import get_virtual_now as gvn
    from backend.app.scheduler.jobs import nudge_job

    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        payload = json.load(fh)["payload"]
    cid = client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(payload)}
    ).json()["case_id"]

    now = gvn() + timedelta(days=5)
    first = nudge_job(now)
    assert {n["nudge_day"] for n in first if n["case_id"] == cid} >= {1, 3}
    second = nudge_job(now)
    assert not [n for n in second if n["case_id"] == cid]
    later = gvn() + timedelta(days=10)
    third = nudge_job(later)
    assert {n["nudge_day"] for n in third if n["case_id"] == cid} >= {7, 10}


def test_deadline_closes_case():
    import json
    from datetime import timedelta

    from backend.app.core.virtual_clock import get_virtual_now as gvn
    from backend.app.scheduler.jobs import deadline_job

    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        payload = json.load(fh)["payload"]
    cid = client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(payload)}
    ).json()["case_id"]
    assert deadline_job(gvn() + timedelta(days=13)) == []
    fired = deadline_job(gvn() + timedelta(days=15))
    assert any(f["case_id"] == cid for f in fired)
    case = client.get(f"/api/v1/cases/{cid}").json()
    assert case["status"] == "REJECTED"
