import asyncio
import json

from backend.app.pipeline.pipeline import run_full


def test_replay_determinism_5x5():
    names = ["hp-1", "ec-1-run-1", "ec-2a", "ec-2b", "ec-2c"]
    for name in names:
        with open(f"backend/tests/golden/fixtures/{name}.json") as fh:
            fx = json.load(fh)
        first = None
        for _ in range(5):
            files = None
            if fx.get("files"):
                import base64

                files = {k: (fn, base64.b64decode(d)) for k, (fn, d) in fx["files"].items()}
            r = asyncio.run(run_full(fx["payload"], files=files))
            findings = sorted(
                r["findings"], key=lambda f: (f.get("check_id", ""), f.get("subject") or "")
            )
            for f in findings:
                f.pop("duration_ms", None)
                f.pop("cached", None)
            dump = json.dumps({"d": r["decision"], "f": findings}, sort_keys=True)
            if first is None:
                first = dump
            assert dump == first, name
