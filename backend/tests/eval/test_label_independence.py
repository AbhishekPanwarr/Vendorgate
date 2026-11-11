"""Label independence: build_dataset must never touch the execution engine."""

from pathlib import Path

import json

import yaml

FORBIDDEN = ["pipeline", "decide", "run_eval", "orchestrator", "run_pipeline"]


def test_no_pipeline_imports():
    source = Path("datagen/build_dataset.py").read_text()
    for f in FORBIDDEN:
        assert f not in source, f"Label independence violation: {f} in build_dataset.py"


def test_labels_from_operator_expected():
    with open("datagen/mutations/catalog.yaml") as fh:
        catalog = {o["id"]: o for o in yaml.safe_load(fh)["operators"]}
    for name in ("dataset_dev.json", "dataset_test.json"):
        with open(f"datagen/out/{name}") as fh:
            dataset = json.load(fh)
        for case in dataset:
            op = case["op"]
            if op is None:
                assert case["expected"]["status"] == "APPROVED"
                continue
            ops = [op] if isinstance(op, str) else op
            exp = [catalog[o]["expected"] for o in ops]
            order = {"APPROVED": 0, "PENDING": 1, "REJECTED": 2}
            statuses = sorted((e["status"] for e in exp), key=order.__getitem__)
            assert case["expected"]["status"] == statuses[-1]
            if len(ops) == 1:
                e = exp[0]
                assert sorted(case["expected"]["awaiting"]) == sorted(e["awaiting"])
                assert sorted(case["expected"]["blocking_reason_codes"]) == sorted(
                    e["blocking_reason_codes"]
                )
