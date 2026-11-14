import json

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.persistence import repo

client = TestClient(create_app())


def _submit(payload, headers=None):
    return client.post(
        "/api/v1/submissions",
        files={},
        data={"payload": json.dumps(payload)},
        headers=headers or {},
    )


def _hp1():
    with open("backend/tests/fixtures/hp1_payload.json") as fh:
        return json.load(fh)


def test_cases_list_and_get():
    repo.STORE["idempotency"].clear()
    r = _submit(_hp1()).json()
    cases = client.get("/api/v1/cases").json()
    assert any(c["case_id"] == r["case_id"] for c in cases)
    case = client.get(f"/api/v1/cases/{r['case_id']}").json()
    assert case["run"]["decision"]["status"] == "APPROVED"
    assert client.get("/api/v1/cases/nope").status_code == 404


def test_audit_and_verify():
    r = _submit(_hp1()).json()
    audit = client.get(f"/api/v1/cases/{r['case_id']}/audit").json()
    assert any(e["type"] == "decision.made" for e in audit)
    v = client.get(f"/api/v1/cases/{r['case_id']}/audit/verify").json()
    assert v["ok"] is True


def test_approvals_sod():
    # requester name is "Dana Whitfield" per hp1 fixture
    r = _submit(_hp1()).json()
    cid = r["case_id"]
    denied = client.post(
        f"/api/v1/cases/{cid}/approvals",
        headers={"X-Actor": "Dana Whitfield", "X-Role": "CONTROLLER"},
    )
    assert denied.status_code == 403
    assert denied.json()["type"] == "SEGREGATION_OF_DUTIES_VIOLATION"
    # second actor on a fresh case: proves actor comparison, not header parsing
    r2 = _submit(_hp1()).json()
    ok = client.post(
        f"/api/v1/cases/{r2['case_id']}/approvals",
        headers={"X-Actor": "Priya Nair", "X-Role": "CONTROLLER"},
    )
    assert ok.status_code == 200


def test_resolutions_role_gate():
    r = _submit(_hp1()).json()
    cid = r["case_id"]
    denied = client.post(
        f"/api/v1/cases/{cid}/resolutions",
        json={"reason_code": "SANCTIONS_REVIEW", "action": "CLEARED"},
        headers={"X-Role": "AP_ANALYST"},
    )
    assert denied.status_code == 403
    ok = client.post(
        f"/api/v1/cases/{cid}/resolutions",
        json={"reason_code": "SANCTIONS_REVIEW", "action": "CLEARED"},
        headers={"X-Role": "COMPLIANCE"},
    )
    assert ok.status_code == 200


def test_callback_422_and_metrics():
    r = _submit(_hp1()).json()
    assert client.post(f"/api/v1/cases/{r['case_id']}/callback", json={}).status_code == 422
    m = client.get("/api/v1/metrics/dashboard").json()
    assert m["volume"] >= 1 and "by_status" in m
    vendors = client.get("/api/v1/vendors").json()
    assert any(v.get("vendor_id") for v in vendors)
