"""Build Phase 1 golden fixtures (run once; committed)."""

from backend.tests.golden.fixture_payloads import base_in  # noqa: F401

from backend.tests.golden.fixture_payloads import base_in
from backend.tests.golden.fixture_payloads import ec18
from backend.tests.golden.fixture_payloads import ec1
from backend.tests.golden.fixture_payloads import ec2a
from backend.tests.golden.fixture_payloads import ec2b
from backend.tests.golden.fixture_payloads import ec2c
from backend.tests.golden.fixture_payloads import hp1
from backend.tests.golden.fixture_payloads import hp3


def main() -> None:
    import asyncio
    import json

    from backend.app.pipeline.pipeline import run_full

    with open("backend/tests/fixtures/hp2_payload.json") as _fh:
        _hp2 = json.load(_fh)
    cases = {
        "hp-1": hp1(),
        "hp-2": _hp2,
        "hp-3": hp3(),
        "ec-1-run-1": ec1(),
        "ec-2a": ec2a(),
        "ec-2b": ec2b(),
        "ec-2c": ec2c(),
        "ec-18": ec18(),
    }
    for name, payload in cases.items():
        r = asyncio.run(run_full(payload))
        d = r["decision"]
        print(name, d["status"], d["tier"], d["score"]["total"], d["reason_codes"])
        with open(f"backend/tests/golden/fixtures/{name}.json", "w") as _fh:
            json.dump(
                {"payload": payload, "decision": d, "findings": r["findings"]},
                _fh,
                indent=1,
            )
    print("fixtures written")


if __name__ == "__main__":
    main()
