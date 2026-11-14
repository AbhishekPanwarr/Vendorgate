import json

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.persistence import repo
from backend.tests.api.test_submissions_skeleton import PAYLOAD

client = TestClient(create_app())


def test_idempotency():
    repo.STORE["idempotency"].clear()
    h = {"Idempotency-Key": "k-1"}
    r1 = client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(PAYLOAD)}, headers=h
    ).json()
    r2 = client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(PAYLOAD)}, headers=h
    ).json()
    assert r1 == r2
    r3 = client.post(
        "/api/v1/submissions",
        files={},
        data={"payload": json.dumps(PAYLOAD)},
        headers={"Idempotency-Key": "k-2"},
    ).json()
    assert r3 != r1


def test_admin_reset():
    r = client.post("/api/v1/admin/reset")
    assert r.status_code == 200
    assert r.json()["duration_ms"] < 5000
