"""E2E: EC-3b callback, EC-3a network, EC-4b message, approvals queue."""

import json
import os
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.skipif(not os.environ.get("VG_BASE_URL"), reason="VG_BASE_URL not set")


def _post(path, payload=None, headers=None):
    base = os.environ["VG_BASE_URL"]
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(
        base + path,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": json.load(e)}


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


def _shot(name, url, wait_text, tab=None):
    base = os.environ["VG_BASE_URL"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(base + url)
        if tab:
            page.get_by_role("tab", name=tab).click()
        page.get_by_text(wait_text).first.wait_for(timeout=8000)
        page.screenshot(path=f"/tmp/shot-{name}.png")
        page.close()


def test_ec3b_callback():
    with open("backend/tests/golden/fixtures/ec-3b.json") as fh:
        fx = json.load(fh)
    r = _submit(fx["payload"])
    cid = r["case_id"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{os.environ['VG_BASE_URL']}/approvals")
        page.get_by_text("Approvals Queue").wait_for(timeout=8000)
        page.get_by_text("Beacon Retail Group Inc").first.click()
        page.get_by_role("button", name="Open Callback Desk").click()
        page.get_by_label("callback number").fill("+442071234567")
        page.get_by_text("From the request form").click()
        page.get_by_text("I dialed this number myself").click()
        page.get_by_role("button", name="Verify Callback").click()
        page.get_by_text("CALLBACK_NOT_INDEPENDENT").wait_for(timeout=5000)
        page.screenshot(path="/tmp/shot-ec3b-cb-bad.png")
        page.get_by_label("callback number").fill("+16145550100")
        page.get_by_text("Vendor master record").click()
        page.get_by_role("button", name="Verify Callback").click()
        page.get_by_text("independent", exact=False).first.wait_for(timeout=8000)
        page.screenshot(path="/tmp/shot-ec3b-cb-good.png")
        page.close()


def test_ec3a_network():
    with open("backend/tests/golden/fixtures/ec-3a.json") as fh:
        fx = json.load(fh)
    r = _submit(fx["payload"])
    _shot("ec3a-network", f"/cases/{r['case_id']}", "shared across vendors", tab="Network")


def test_ec4b_message():
    with open("backend/tests/golden/fixtures/ec-4b.json") as fh:
        fx = json.load(fh)
    r = _submit(fx["payload"])
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{os.environ['VG_BASE_URL']}/cases/{r['case_id']}")
        page.get_by_text("REJECTED").first.wait_for(timeout=8000)
        page.get_by_role("tab", name="Message").click()
        page.get_by_text("compliance review").wait_for(timeout=5000)
        page.screenshot(path="/tmp/shot-ec4b-msg.png")
        page.close()


def test_approvals_queue():
    base = os.environ["VG_BASE_URL"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(base + "/approvals")
        page.get_by_text("Approvals queue").wait_for(timeout=8000)
        page.screenshot(path="/tmp/shot-approvals.png")
        page.close()
