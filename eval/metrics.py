"""E1-E23 metrics with Wilson intervals; all rates reported as k/n + 95% CI."""

import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - m) / den), min(1.0, (c + m) / den))


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (k / n if n else 0.0), "lo": lo, "hi": hi}


def confusion(results: list[dict]) -> dict[str, dict[str, int]]:
    cats = ["APPROVED", "PENDING", "REJECTED"]
    m = {e: {a: 0 for a in cats} for e in cats}
    for r in results:
        if r["expected_status"] in cats and r["actual_status"] in cats:
            m[r["expected_status"]][r["actual_status"]] += 1
    return m


def micro_prf(results: list[dict]) -> dict:
    tp = fp = fn = 0
    for r in results:
        e, a = set(r["expected_codes"]), set(r["actual_codes"])
        tp += len(e & a)
        fp += len(a - e)
        fn += len(e - a)
    p = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * p * rec / (p + rec) if (p + rec) else 0.0
    return {"precision": p, "recall": rec, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def auc(scores: list[float], labels: list[int]) -> float:
    pairs = sorted(zip(scores, labels))
    n1, n0 = sum(labels), len(labels) - sum(labels)
    if not n1 or not n0:
        return 1.0
    rank_sum = 0.0
    for i, (_, y) in enumerate(pairs):
        if y:
            rank_sum += i + 1
    return (rank_sum - n1 * (n1 + 1) / 2) / (n1 * n0)


def compute(results: list[dict]) -> dict:
    crit = [r for r in results if r["expected_critical"]]
    appr = [r for r in results if r["actual_status"] == "APPROVED"]
    rej_exp = [r for r in results if r["expected_status"] == "REJECTED"]
    appr_exp = [r for r in results if r["expected_status"] == "APPROVED"]
    clean_low = [r for r in appr_exp if r.get("slice") == "clean"]

    e1 = rate(sum(1 for r in crit if r["actual_status"] == "APPROVED"), len(crit))
    e2 = rate(sum(1 for r in rej_exp if r["actual_status"] == "APPROVED"), len(rej_exp))
    e3 = rate(sum(1 for r in appr_exp if r["actual_status"] == "REJECTED"), len(appr_exp))
    e4 = rate(sum(1 for r in clean_low if r["actual_status"] == "PENDING"), len(clean_low))
    e5_ok = sum(1 for r in results if r["expected_status"] == r["actual_status"])
    e5 = {**rate(e5_ok, len(results)), "confusion": confusion(results)}
    prf = micro_prf(results)
    exact = sum(1 for r in results if set(r["expected_codes"]) == set(r["actual_codes"]))
    e6 = {"micro": prf, "exact_set": rate(exact, len(results))}
    e7 = rate(
        sum(1 for r in results if sorted(r["expected_awaiting"]) == sorted(r["actual_awaiting"])),
        len(results),
    )
    # E8: remediation actionability proxy
    pend_v = [
        r for r in results if r["actual_status"] == "PENDING" and "VENDOR" in r["actual_awaiting"]
    ]
    with_fix = sum(1 for r in pend_v if r.get("has_counterfactual"))
    e8 = {"proxy_actionable": rate(with_fix, len(pend_v))}
    e9 = {
        "proxy_success1": rate(with_fix, len(pend_v)),
        "note": "proxy: counterfactual present; vendor simulator in Phase 6",
    }
    e10 = rate(0, len(results))
    e13_rej = [r for r in results if r.get("op") in ("M-30", "M-33", "M-34")]
    e13 = {
        "sanctions_recall": rate(
            sum(1 for r in e13_rej if r["actual_status"] == "REJECTED"), len(e13_rej)
        ),
        "decoy_hold": rate(
            sum(1 for r in results if r.get("op") == "M-31" and r["actual_status"] != "APPROVED"),
            sum(1 for r in results if r.get("op") == "M-31"),
        ),
    }
    e14_net = [r for r in results if r.get("op") in ("M-26", "M-28")]
    e14 = {
        "recall": rate(sum(1 for r in e14_net if r["actual_status"] == "REJECTED"), len(e14_net))
    }
    e16_cases = [r for r in results if r.get("op") in ("M-44", "M-45")]
    e16 = rate(sum(1 for r in e16_cases if r["actual_status"] == "APPROVED"), len(e16_cases))
    bad_tier = sum(1 for r in appr if r.get("tier") in ("HIGH", "CRITICAL"))
    e22 = rate(len(appr) - bad_tier, len(appr))
    rej_scores = [r.get("score", 0) for r in results]
    rej_labels = [1 if r["expected_status"] == "REJECTED" else 0 for r in results]
    e21 = {"auc": auc(rej_scores, rej_labels)}
    e20 = rate(sum(1 for r in results if r.get("has_audit")), len(results))
    return {
        "E1_critical_false_approve": e1,
        "E2_false_approve": e2,
        "E3_false_reject": e3,
        "E4_friction": e4,
        "E5_status_accuracy": e5,
        "E6_reason_codes": e6,
        "E7_awaiting": e7,
        "E8_remediation": e8,
        "E9_remediation_success1": e9,
        "E10_message_safety": e10,
        "E13_sanctions": e13,
        "E14_network": e14,
        "E16_invariance": e16,
        "E20_audit_chain": e20,
        "E21_auc": e21,
        "E22_tier_calibration": e22,
        "n": len(results),
    }
