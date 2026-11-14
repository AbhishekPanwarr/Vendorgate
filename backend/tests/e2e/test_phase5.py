"""E2E: Benchmark, Fool-it Lab, Policy pages + JSON parity."""

import json
import os
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.skipif(not os.environ.get("VG_BASE_URL"), reason="VG_BASE_URL not set")


def _shot(name, url, wait_text, click=None):
    base = os.environ["VG_BASE_URL"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(base + url)
        if click:
            page.get_by_role("button", name=click, exact=True).click()
        page.get_by_text(wait_text).first.wait_for(timeout=10000)
        page.screenshot(path=f"/tmp/shot-{name}.png")
        body = page.content()
        page.close()
        return body


def test_benchmark_page_and_parity():
    with open("eval/reports/latest.json") as fh:
        latest = json.load(fh)
    e1 = latest["test_hybrid"]["E1_critical_false_approve"]
    e1_text = f"{e1['rate'] * 100:.1f}% ({e1['k']}/{e1['n']})"
    body = _shot("benchmark", "/benchmark", "Benchmark")
    assert e1_text in body  # parity: page number comes from latest.json
    assert "Ablation" in body
    assert "Limitations" in body


def test_foolit_lab():
    base = os.environ["VG_BASE_URL"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
        page.goto(base + "/foolit")
        page.get_by_text("Fool-it Lab").wait_for(timeout=10000)
        page.get_by_text("M-06").click()
        page.get_by_test_id("run").click()
        page.get_by_test_id("result").wait_for(timeout=120000)
        txt = page.get_by_test_id("result").inner_text()
        assert "PENDING" in txt
        assert page.get_by_test_id("crit-approvals").inner_text() == "0"
        page.screenshot(path="/tmp/shot-foolit.png")
        page.close()


def test_policy_page():
    latest_policy = json.load(urllib.request.urlopen(os.environ["VG_BASE_URL"] + "/api/v1/policy"))
    assert len(latest_policy["assumptions"]) == 15
    body = _shot("policy", "/policy", "A-01")
    assert latest_policy["policy_hash"][:12] in body
    assert "A-15" in body
