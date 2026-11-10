"""Golden snapshots: full pipeline replay vs committed fixtures."""

import asyncio
import json

import pytest

from backend.app.pipeline.pipeline import run_full

NAMES = ["hp-1", "hp-2", "hp-3", "ec-1-run-1", "ec-2a", "ec-2b", "ec-2c", "ec-18"]


def strip_volatile(result: dict) -> dict:
    out = {"decision": result["decision"], "findings": []}
    for f in result["findings"]:
        out["findings"].append(
            {k: v for k, v in f.items() if k not in ("duration_ms", "cached", "fingerprint")}
        )
    return out


def strip_fixture(fx: dict) -> dict:
    return strip_volatile({"decision": fx["decision"], "findings": fx["findings"]})


@pytest.mark.parametrize("name", NAMES)
def test_golden(name, request):
    with open(f"backend/tests/golden/fixtures/{name}.json") as fh:
        fx = json.load(fh)
    result = asyncio.run(run_full(fx["payload"]))
    if request.config.getoption("--update-goldens"):
        with open(f"backend/tests/golden/fixtures/{name}.json", "w") as fh:
            json.dump(
                {
                    "payload": fx["payload"],
                    "decision": result["decision"],
                    "findings": result["findings"],
                },
                fh,
                indent=1,
            )
        pytest.skip("golden regenerated (review diff before commit)")
    assert strip_volatile(result) == strip_fixture(fx)
