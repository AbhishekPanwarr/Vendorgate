import json
import re
from pathlib import Path

import yaml


def test_catalog():
    cat = yaml.safe_load(Path("datagen/mutations/catalog.yaml").read_text())
    ops = cat["operators"]
    assert len(ops) == 48
    ids = [o["id"] for o in ops]
    assert len(set(ids)) == 48
    assert all(re.match(r"^M-\d{2}$", i) for i in ids)
    for o in ops:
        assert set(o) >= {
            "id",
            "name",
            "description",
            "applies_to",
            "conflicts_with",
            "phase",
            "expected",
        }
        assert o["phase"] in ("P0", "P1")
        for c in o["expected"]["blocking_reason_codes"]:
            assert re.match(r"^[A-Z][A-Z0-9_]+$", c), c
    truth = json.loads(Path("backend/tests/contract/fixtures/mutation_truth.json").read_text())
    tmap = {r["id"]: r for r in truth}
    assert len(tmap) == 48
    for o in ops:
        t = tmap[o["id"]]
        e = o["expected"]
        assert t["status"] == e["status"]
        assert t["awaiting"] == e["awaiting"]
        assert t["reason_codes"] == e["blocking_reason_codes"]
        assert t["critical"] == e["critical"]
