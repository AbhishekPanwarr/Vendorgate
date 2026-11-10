"""Playwright skeleton smoke vs deployed URL (VG_BASE_URL)."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("VG_BASE_URL"), reason="VG_BASE_URL not set (Render creds pending)"
)


def test_skeleton_smoke(page):
    base = os.environ["VG_BASE_URL"]
    page.goto(base + "/")
    page.get_by_label("legal name").fill("Test Vendor")
    page.get_by_role("button", name="Submit").click()
    page.wait_for_url("**/runs/*", timeout=5000)
    page.get_by_role("status").wait_for(timeout=5000)
