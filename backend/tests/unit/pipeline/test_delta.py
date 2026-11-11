from backend.app.pipeline.delta import changed_paths
from backend.app.pipeline.delta import compute_delta


def _f(check_id, outcome, reads=(), subject=None):
    return {
        "check_id": check_id,
        "subject": subject,
        "outcome": outcome,
        "mandatory": True,
        "reads": list(reads),
        "reason_code": "R",
    }


def test_changed_paths():
    old = {"a": 1, "b": {"c": 2}, "documents": [{"doc_type": "W9"}]}
    new = {"a": 1, "b": {"c": 3}, "documents": [{"doc_type": "W9"}]}
    assert changed_paths(old, new) == {"b.c"}
    assert changed_paths(old, old) == set()


def test_rerun_cached_counts():
    old = [_f("C-A", "FAIL", ["x"]), _f("C-B", "PASS", ["y"])]
    new = [_f("C-A", "FAIL", ["x"]), _f("C-B", "PASS", ["y"])]
    d = compute_delta(old, new, {"z"}, rerun=0, cached=2)
    assert (d["rerun"], d["cached"]) == (0, 2)
    assert d["resolved"] == [] and d["introduced"] == []


def test_resolved_on_clear():
    old = [_f("C-A", "FAIL", ["x"])]
    new = [_f("C-A", "WARN", ["x"])]
    d = compute_delta(old, new, {"x"}, 1, 0)
    assert d["resolved"] == ["C-A"] and d["introduced"] == []


def test_introduced_only_if_reads_intersect():
    old = [_f("C-A", "PASS", ["x"])]
    new = [_f("C-A", "FAIL", ["x"]), _f("C-B", "FAIL", ["unrelated"])]
    d = compute_delta(old, new, {"x"}, 2, 0)
    assert d["introduced"] == ["C-A"]


def test_not_introduced_without_intersection():
    old = []
    new = [_f("C-A", "FAIL", ["unrelated"])]
    d = compute_delta(old, new, {"x"}, 1, 0)
    assert d["introduced"] == []
