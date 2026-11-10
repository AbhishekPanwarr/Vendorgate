from fastapi.testclient import TestClient

from backend.app.decision.routing import check_callback
from backend.app.main import create_app

client = TestClient(create_app())


def test_independence_matrix():
    req_phones = ["+16145550001"]
    assert (
        check_callback("+16145550001", "VENDOR_MASTER", req_phones, 60, 30, True)["reason"]
        == "CALLBACK_NOT_INDEPENDENT"
    )
    assert (
        check_callback("+16145550002", "FROM_REQUEST", req_phones, 60, 30, True)["reason"]
        == "CALLBACK_NOT_INDEPENDENT"
    )
    assert (
        check_callback("+16145550002", "VENDOR_MASTER", req_phones, 10, 30, True)["reason"]
        == "CALLBACK_NUMBER_TOO_NEW"
    )
    assert (
        check_callback("+16145550002", "VENDOR_MASTER", req_phones, 60, 30, False)["reason"]
        == "ATTESTATION_REQUIRED"
    )
    assert check_callback("+16145550002", "VENDOR_MASTER", req_phones, 60, 30, True)["ok"] is True
    assert check_callback("+16145550002", "REGISTRY", req_phones, 30, 30, True)["ok"] is True
    assert (
        check_callback("+16145550002", "PUBLIC_DIRECTORY", req_phones, 90, 30, True)["ok"] is True
    )
    assert (
        check_callback("+16145550002", "VENDOR_MASTER", [], 0, 30, True)["reason"]
        == "CALLBACK_NUMBER_TOO_NEW"
    )


def test_callback_api_flow():
    import json

    from backend.tests.api.test_cases import _hp1

    r = client.post("/api/v1/submissions", files={}, data={"payload": json.dumps(_hp1())}).json()
    cid = r["case_id"]
    bad = client.post(
        f"/api/v1/cases/{cid}/callback",
        json={
            "number_used": "+16145550142",
            "number_source": "VENDOR_MASTER",
            "outcome": "verified",
            "attested": True,
            "number_age_days": 60,
        },
    ).json()
    assert bad["ok"] is False  # request phone, not independent
    good = client.post(
        f"/api/v1/cases/{cid}/callback",
        json={
            "number_used": "+16145550999",
            "number_source": "REGISTRY",
            "outcome": "verified",
            "attested": True,
            "number_age_days": 60,
        },
    ).json()
    assert good["ok"] is True
    assert good["cleared"] == ["BANK_CHANGE_REQUIRES_CALLBACK", "CALLBACK_REQUIRED"]
