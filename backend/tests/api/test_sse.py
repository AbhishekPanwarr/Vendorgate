import json

from fastapi.testclient import TestClient

from backend.app.main import create_app

client = TestClient(create_app())

PAYLOAD = {
    "schema_version": "1.0",
    "submission_type": "NEW_VENDOR",
    "existing_vendor_id": None,
    "requester": {
        "name": "D",
        "email": "d@b.co",
        "department": "F",
        "business_justification": "j",
        "expected_annual_spend": {"amount": 100, "currency": "USD"},
        "category": "OFFICE_SUPPLIES",
        "data_access": False,
        "one_time": False,
    },
    "company": {
        "legal_name": "Acme LLC",
        "trading_name": None,
        "entity_type": "LLC",
        "country": "US",
        "incorporation_date": "2020-01-01",
        "registered_address": {
            "line1": "1 Main",
            "line2": None,
            "city": "C",
            "region": "OH",
            "postal_code": "43215",
            "country": "US",
        },
        "remit_to_address": None,
        "website": None,
        "primary_contact": {"name": "A", "email": "a@x.com", "phone": "+16145550142"},
        "ap_contact": {"name": "B", "email": "b@x.com", "phone": "+16145550143"},
        "owners": [],
    },
    "tax": {
        "country": "US",
        "tax_id_type": "EIN",
        "tax_id": "12-3456789",
        "secondary_ids": {},
        "tax_classification": "LLC",
        "form_type": "W9",
        "vat_id": None,
    },
    "bank": {
        "country": "US",
        "currency": "USD",
        "account_holder_name": "Acme LLC",
        "bank_name": "B",
        "account_number": "000123456789",
        "routing_number": "011000015",
        "iban": None,
        "swift_bic": None,
        "ifsc": None,
        "sort_code": None,
    },
    "documents": [],
    "declarations": {},
    "submitter_meta": {},
}


def _submit():
    return client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(PAYLOAD)}
    ).json()


def test_sse_stream():
    run_id = _submit()["run_id"]
    r = client.get(f"/api/v1/runs/{run_id}/events")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    assert "id: 1" in r.text and ": hb" in r.text


def test_sse_reconnect():
    run_id = _submit()["run_id"]
    r = client.get(f"/api/v1/runs/{run_id}/events", headers={"Last-Event-ID": "2"})
    assert "id: 3" in r.text
    assert "\nid: 1\n" not in r.text and "\nid: 2\n" not in r.text
