from fastapi.testclient import TestClient

from backend.app.main import create_app

client = TestClient(create_app())


def test_admin_reset_timing():
    r = client.post("/api/v1/admin/reset")
    assert r.status_code == 200
    assert r.json()["duration_ms"] < 5000
