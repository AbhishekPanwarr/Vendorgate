import json

from fastapi.testclient import TestClient

from backend.app.decision.routing import check_appeal_sod
from backend.app.main import create_app

client = TestClient(create_app())


def test_appeal_3role_sod_pure():
    req = "Dana Whitfield"
    assert check_appeal_sod(req, [], "Priya Nair") is True
    assert check_appeal_sod(req, [], "Dana Whitfield") is False
    assert check_appeal_sod(req, ["Priya Nair"], "Priya Nair") is False
    assert check_appeal_sod(req, ["Priya Nair"], "Asha Rao") is True


def test_idempotent_replayed_header():
    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        payload = json.load(fh)["payload"]
    cid = client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(payload)}
    ).json()["case_id"]
    p2 = json.loads(json.dumps(payload))
    p2["company"]["trading_name"] = "Acme Trading"
    h = {"If-Match": "1", "Idempotency-Key": "idem-hdr-1"}
    r1 = client.post(
        f"/api/v1/cases/{cid}/resubmit", files={}, data={"payload": json.dumps(p2)}, headers=h
    )
    assert r1.status_code == 202
    assert "Idempotent-Replayed" not in r1.headers
    r2 = client.post(
        f"/api/v1/cases/{cid}/resubmit", files={}, data={"payload": json.dumps(p2)}, headers=h
    )
    assert r2.json() == r1.json()
    assert r2.headers.get("Idempotent-Replayed") == "true"
