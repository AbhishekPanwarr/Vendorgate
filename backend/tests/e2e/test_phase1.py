"""E2E: case page + dashboard vs local server (VG_BASE_URL). Uses sync playwright."""

import json
import os
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.skipif(not os.environ.get("VG_BASE_URL"), reason="VG_BASE_URL not set")


def _submit(payload):
    base = os.environ["VG_BASE_URL"]
    body = (
        '--B\r\nContent-Disposition: form-data; name="payload"\r\n\r\n'
        + json.dumps(payload)
        + "\r\n--B--\r\n"
    ).encode()
    req = urllib.request.Request(
        base + "/api/v1/submissions",
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=B"},
        method="POST",
    )
    return json.load(urllib.request.urlopen(req))


def test_case_page_smoke():
    base = os.environ["VG_BASE_URL"]
    with open("backend/tests/fixtures/hp1_payload.json") as fh:
        r = _submit(json.load(fh))
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.goto(f"{base}/cases/{r['case_id']}")
        page.get_by_text("APPROVED").first.wait_for(timeout=8000)
        page.get_by_text("Score waterfall").wait_for(timeout=5000)
        page.get_by_role("button", name="audit", exact=True).click()
        page.get_by_role("button", name="Verify chain").click()
        page.get_by_text("chain ok").wait_for(timeout=5000)
        page.close()


def test_ec1_case():
    base = os.environ["VG_BASE_URL"]
    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        fx = json.load(fh)
    r = _submit(fx["payload"])
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.goto(f"{base}/cases/{r['case_id']}")
        page.get_by_text("PENDING").first.wait_for(timeout=8000)
        page.get_by_text("Blocking items").wait_for(timeout=5000)
        page.close()


def test_dashboard():
    base = os.environ["VG_BASE_URL"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.goto(base + "/")
        page.get_by_text("VendorGate dashboard").wait_for(timeout=8000)
        page.get_by_text("Runs").wait_for(timeout=5000)
        page.close()
