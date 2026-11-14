"""Build EC-13 (retry+appeal), EC-14 (nudges+deadline), EC-3b-delta goldens."""

import copy
import json
from datetime import timedelta

from fastapi.testclient import TestClient

from backend.app.core.virtual_clock import get_virtual_now
from backend.app.main import create_app
from backend.app.scheduler.jobs import deadline_job
from backend.app.scheduler.jobs import nudge_job

client = TestClient(create_app())


def _submit(payload):
    return client.post(
        "/api/v1/submissions", files={}, data={"payload": json.dumps(payload)}
    ).json()


def ec13():
    base = json.load(open("backend/tests/golden/fixtures/ec-2b.json"))["payload"]
    r = _submit(base)
    cid = r["case_id"]
    # 4 resubmits varying an unrelated field; GSTIN checksum stays bad.
    # attempt counts per reason code: 4th submit sees 3 priors -> RETRY_LIMIT.
    for i in range(4):
        v = copy.deepcopy(base)
        v["company"]["trading_name"] = f"Attempt {i}"
        rr = client.post(
            f"/api/v1/cases/{cid}/resubmit",
            files={},
            data={"payload": json.dumps(v)},
            headers={"If-Match": str(i + 1), "Idempotency-Key": f"ec13-{i}"},
        )
        assert rr.status_code == 202, rr.text
    case = client.get(f"/api/v1/cases/{cid}").json()
    ap = client.post(
        f"/api/v1/cases/{cid}/appeal",
        json={"reason": "typo fixed"},
        headers={"X-Actor": "Priya Nair"},
    )
    return (
        cid,
        case,
        ap.json() if ap.status_code == 202 else {"status": ap.status_code, "body": ap.json()},
    )


def ec14():
    base = json.load(open("backend/tests/golden/fixtures/ec-1-run-1.json"))["payload"]
    r = _submit(base)
    cid = r["case_id"]
    base_now = get_virtual_now()
    fired = []
    for days in (1, 3, 7, 10):
        fired += nudge_job(base_now + timedelta(days=days))
    closed = deadline_job(base_now + timedelta(days=15))
    case = client.get(f"/api/v1/cases/{cid}").json()
    return cid, fired, closed, case


def ec3b_delta():
    fx = json.load(open("backend/tests/golden/fixtures/ec-3b.json"))
    r = _submit(fx["payload"])
    cid = r["case_id"]
    cb_bad = client.post(
        f"/api/v1/cases/{cid}/callback",
        json={
            "number_used": "+16145550142",
            "number_source": "VENDOR_MASTER",
            "outcome": "verified",
            "attested": True,
            "number_age_days": 60,
        },
    ).json()
    cb_good = client.post(
        f"/api/v1/cases/{cid}/callback",
        json={
            "number_used": "+16145550100",
            "number_source": "VENDOR_MASTER",
            "outcome": "verified",
            "attested": True,
            "number_age_days": 60,
        },
    ).json()
    ap = client.post(
        f"/api/v1/cases/{cid}/approvals", headers={"X-Actor": "Priya Nair", "X-Role": "CONTROLLER"}
    ).json()
    case = client.get(f"/api/v1/cases/{cid}").json()
    return cid, cb_bad, cb_good, ap, case


def main() -> None:
    cid, case, ap = ec13()
    print("ec-13:", case["status"], case.get("reason_codes"), "| appeal:", ap.get("status"))
    json.dump(
        {"case_id": cid, "status": case["status"], "appeal": ap},
        open("backend/tests/golden/fixtures/ec-13.json", "w"),
        indent=1,
    )
    cid, fired, closed, case = ec14()
    print(
        "ec-14:",
        case["status"],
        "| nudges:",
        len([f for f in fired if f["case_id"] == cid]),
        "| closed:",
        bool([c for c in closed if c["case_id"] == cid]),
    )
    json.dump(
        {
            "case_id": cid,
            "status": case["status"],
            "nudges": [f for f in fired if f["case_id"] == cid],
            "closed": closed,
        },
        open("backend/tests/golden/fixtures/ec-14.json", "w"),
        indent=1,
    )
    cid, bad, good, ap, case = ec3b_delta()
    print("ec-3b-delta:", case["status"], "| bad:", bad, "| good-ok:", good.get("ok"))
    json.dump(
        {"case_id": cid, "status": case["status"], "cb_bad": bad, "cb_good": good, "approval": ap},
        open("backend/tests/golden/fixtures/ec-3b-delta.json", "w"),
        indent=1,
    )
    print("phase4 EC goldens written")


if __name__ == "__main__":
    main()
