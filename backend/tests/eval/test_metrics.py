"""E1-E23 metric unit tests with hand-computed reference values."""

from eval.metrics import auc, compute, rate, wilson


def test_wilson_reference():
    lo, hi = wilson(0, 100)
    assert lo == 0.0 and hi > 0.03 and hi < 0.04  # ~3/100 rule
    lo, hi = wilson(50, 100)
    assert 0.40 < lo < 0.41 and 0.59 < hi < 0.60


def _r(
    exp_status,
    actual_status,
    codes_e=(),
    codes_a=(),
    awaiting_e=(),
    awaiting_a=(),
    critical=False,
    op=None,
    tier="LOW",
):
    return {
        "expected_status": exp_status,
        "actual_status": actual_status,
        "expected_codes": list(codes_e),
        "actual_codes": list(codes_a),
        "expected_awaiting": list(awaiting_e),
        "actual_awaiting": list(awaiting_a),
        "expected_critical": critical,
        "op": op,
        "tier": tier,
        "score": 10,
        "has_counterfactual": False,
        "has_audit": True,
        "n_blocking": len(codes_a),
        "seconds": 0.1,
    }


def test_e1_e5_reference():
    results = (
        [_r("PENDING", "PENDING", ("A",), ("A",), ("VENDOR",), ("VENDOR",))]
        + [_r("APPROVED", "APPROVED", (), (), (), ())]
        + [_r("REJECTED", "APPROVED", ("X",), (), (), (), critical=True, op="M-30")]
    )
    m = compute(results)
    assert m["E1_critical_false_approve"]["k"] == 1
    assert m["E1_critical_false_approve"]["n"] == 1
    assert m["E5_status_accuracy"]["k"] == 2
    assert m["E6_reason_codes"]["micro"]["tp"] == 1
    assert m["E6_reason_codes"]["micro"]["fp"] == 0
    assert m["E6_reason_codes"]["micro"]["fn"] == 1


def test_auc_reference():
    assert auc([1.0, 2.0, 3.0, 4.0], [0, 0, 1, 1]) == 1.0
    assert auc([1.0, 2.0], [0, 0]) == 1.0  # degenerate: no positives


def test_rate_shape():
    r = rate(3, 10)
    assert r["k"] == 3 and r["n"] == 10 and abs(r["rate"] - 0.3) < 1e-9
    assert r["lo"] <= 0.3 <= r["hi"]
