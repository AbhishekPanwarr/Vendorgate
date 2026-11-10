from fastapi.testclient import TestClient

from backend.app.main import create_app

client = TestClient(create_app())


def test_health():
    assert client.get("/healthz").json() == {"ok": True}


def test_readyz():
    r = client.get("/readyz")
    assert r.status_code == 200
