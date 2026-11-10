"""E2E: EC-1 resubmit (APPROVED+K3), EC-5 injection doc, adjudication badge."""

import base64
import json
import os

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.skipif(not os.environ.get("VG_BASE_URL"), reason="VG_BASE_URL not set")


def _submit_fixture(name):
    base = os.environ["VG_BASE_URL"]
    with open(f"backend/tests/golden/fixtures/{name}.json") as fh:
        fx = json.load(fh)
    import urllib.request

    boundary = "BND"
    chunks = []
    chunks.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="payload"\r\n\r\n'.encode()
        + json.dumps(fx["payload"]).encode()
        + b"\r\n"
    )
    for doc_id, (fn, b64) in fx.get("files", {}).items():
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="file:{doc_id}"; '
            f'filename="{fn}"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
            + base64.b64decode(b64)
            + b"\r\n"
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        base + "/api/v1/submissions",
        data=b"".join(chunks),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    return json.load(urllib.request.urlopen(req))


def test_ec1_resubmit():
    base = os.environ["VG_BASE_URL"]
    r = _submit_fixture("ec-1-resubmit")
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base}/cases/{r['case_id']}")
        page.get_by_text("APPROVED").first.wait_for(timeout=8000)
        page.get_by_text("S8 adjudication: SAME").wait_for(timeout=5000)
        page.screenshot(path="/tmp/shot-ec1-resubmit.png")
        page.close()


def test_ec5_injection():
    base = os.environ["VG_BASE_URL"]
    r = _submit_fixture("ec-5")
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base}/cases/{r['case_id']}")
        page.get_by_text("PENDING").first.wait_for(timeout=8000)
        page.get_by_role("button", name="network", exact=True).click()
        page.screenshot(path="/tmp/shot-ec5.png")
        page.close()
