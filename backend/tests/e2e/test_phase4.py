"""E2E: resubmit delta view, 409 toast, nudge history, appeals queue."""

import json
import os

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.skipif(not os.environ.get("VG_BASE_URL"), reason="VG_BASE_URL not set")


def _post(path, payload, headers=None):
    import urllib.request

    base = os.environ["VG_BASE_URL"]
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        return {"http_error": e.code}


def _submit(payload):
    import urllib.request

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


def _shot(name, url, wait_text, click=None):
    base = os.environ["VG_BASE_URL"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(base + url)
        if click:
            page.get_by_role("button", name=click, exact=True).click()
        page.get_by_text(wait_text).first.wait_for(timeout=8000)
        page.screenshot(path=f"/tmp/shot-{name}.png")
        page.close()


def test_ec1_resubmit_delta():

    base = os.environ["VG_BASE_URL"]
    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        payload = json.load(fh)["payload"]
    r = _submit(payload)
    cid = r["case_id"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base}/cases/{cid}")
        page.get_by_text("PENDING").first.wait_for(timeout=8000)
        page.get_by_role("button", name="message", exact=True).click()
        page.get_by_role("button", name="Resubmit unchanged (expect 409)").click()
        page.get_by_text("No changes detected").wait_for(timeout=8000)
        page.screenshot(path="/tmp/shot-resubmit-409.png")
        page.close()


def test_nudge_history():
    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        payload = json.load(fh)["payload"]
    r = _submit(payload)
    _post("/api/v1/admin/clock/advance", {"days": 5})
    _shot("nudge-history", f"/cases/{r['case_id']}", "nudge.sent", click="audit")


def test_appeals_queue():
    base = os.environ["VG_BASE_URL"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(base + "/approvals")
        page.get_by_text("Approvals queue").wait_for(timeout=8000)
        page.screenshot(path="/tmp/shot-appeals.png")
        page.close()
