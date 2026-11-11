import json

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.persistence import repo

client = TestClient(create_app())


def _hp1():
    with open("backend/tests/fixtures/hp1_payload.json") as fh:
        return json.load(fh)


def _pending_case():
    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        fx = json.load(fh)
    r = client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(fx["payload"])}
    ).json()
    assert r["case_id"]
    case = client.get(f"/api/v1/cases/{r['case_id']}").json()
    assert case["status"] == "PENDING"
    return r["case_id"], fx["payload"]


def test_resubmit_version_mismatch():
    cid, _ = _pending_case()
    r = client.post(
        f"/api/v1/cases/{cid}/resubmit",
        files={},
        data={"payload": json.dumps(_hp1())},
        headers={"If-Match": "99"},
    )
    assert r.status_code == 412
    assert r.json()["type"] == "VERSION_MISMATCH"


def test_resubmit_no_changes():
    cid, payload = _pending_case()
    r = client.post(
        f"/api/v1/cases/{cid}/resubmit",
        files={},
        data={"payload": json.dumps(payload)},
        headers={"If-Match": "1"},
    )
    assert r.status_code == 409
    assert r.json()["type"] == "NO_CHANGES"


def test_resubmit_not_resubmittable():
    r = client.post("/api/v1/submissions", files={}, data={"payload": json.dumps(_hp1())}).json()
    case = client.get(f"/api/v1/cases/{r['case_id']}").json()
    assert case["status"] == "APPROVED"
    denied = client.post(
        f"/api/v1/cases/{r['case_id']}/resubmit",
        files={},
        data={"payload": json.dumps(_hp1())},
        headers={"If-Match": "1"},
    )
    assert denied.status_code == 403


def test_resubmit_ok_and_idempotent():
    cid, payload = _pending_case()
    payload2 = json.loads(json.dumps(payload))
    payload2["company"]["trading_name"] = "Acme Trading"
    h = {"If-Match": "1", "Idempotency-Key": "rs-1"}
    r1 = client.post(
        f"/api/v1/cases/{cid}/resubmit", files={}, data={"payload": json.dumps(payload2)}, headers=h
    )
    assert r1.status_code == 202
    assert r1.json()["new_version"] == 2
    r2 = client.post(
        f"/api/v1/cases/{cid}/resubmit", files={}, data={"payload": json.dumps(payload2)}, headers=h
    )
    assert r2.json() == r1.json()
    case = client.get(f"/api/v1/cases/{cid}").json()
    assert case["current_version"] == 2
    _ = repo
