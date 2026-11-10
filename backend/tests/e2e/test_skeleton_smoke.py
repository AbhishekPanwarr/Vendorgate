"""Skeleton smoke vs deployed URL (VG_BASE_URL). Uses sync playwright."""

import os

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.skipif(not os.environ.get("VG_BASE_URL"), reason="VG_BASE_URL not set")


def test_skeleton_smoke():
    base = os.environ["VG_BASE_URL"]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.goto(base + "/submit")
        page.get_by_label("legal name").fill("Test Vendor")
        page.get_by_role("button", name="Submit").click()
        page.wait_for_url("**/runs/*", timeout=8000)
        page.close()
