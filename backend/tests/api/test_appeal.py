import json

from fastapi.testclient import TestClient

from backend.app.main import create_app

client = TestClient(create_app())


def _ec3a_case():
    with open("backend/tests/golden/fixtures/ec-3a.json") as fh:
        payload = json.load(fh)["payload"]
    return client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(payload)}
    ).json()["case_id"]


def test_appeal_flow_and_sod():
    cid = _ec3a_case()
    assert client.get(f"/api/v1/cases/{cid}").json()["status"] == "REJECTED"
    # requester cannot review own appeal
    denied = client.post(
        f"/api/v1/cases/{cid}/appeal",
        json={"reason": "we are legit"},
        headers={"X-Actor": "Dana Whitfield"},
    )
    assert denied.status_code == 403
    ok = client.post(
        f"/api/v1/cases/{cid}/appeal",
        json={"reason": "we are legit"},
        headers={"X-Actor": "Priya Nair"},
    )
    assert ok.status_code == 202
    assert ok.json()["awaiting"] == ["INTERNAL"]
    assert client.get(f"/api/v1/cases/{cid}").json()["status"] == "PENDING"


def test_appeal_not_appealable():
    with open("backend/tests/fixtures/hp1_payload.json") as fh:
        payload = json.load(fh)
    cid = client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(payload)}
    ).json()["case_id"]
    r = client.post(
        f"/api/v1/cases/{cid}/appeal", json={"reason": "x"}, headers={"X-Actor": "Priya Nair"}
    )
    assert r.status_code == 403
    assert r.json()["type"] == "NOT_APPEALABLE"
