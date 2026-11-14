"""llm-only baseline on a 25-case stratified slice (LLM budget cap: ~25 calls).

First run is live; verdicts are recorded to fixtures so every later run is
replay (0 live calls). Rerun live only to refresh fixtures deliberately.
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from eval.metrics import compute
from eval.run_eval import llm_only, result_of

OUT = Path("eval/reports")
FIX = OUT / "llm-only-fixtures.json"
N = 25


def case_key(case: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "p": case["payload"],
                "op": case["op"],
                "degraded": sorted((case.get("degraded") or {}).keys()),
            },
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()[:16]


def sample(test: list[dict]) -> list[dict]:
    import random

    rng = random.Random(7)
    crit = [c for c in test if c["expected"]["critical"]]
    rej = [
        c for c in test if c["expected"]["status"] == "REJECTED" and not c["expected"]["critical"]
    ]
    pend = [c for c in test if c["expected"]["status"] == "PENDING"][:900]
    appr = [c for c in test if c["expected"]["status"] == "APPROVED"]
    picks = (
        rng.sample(crit, min(8, len(crit)))
        + rng.sample(rej, min(4, len(rej)))
        + rng.sample(pend, 8)
        + rng.sample(appr, 5)
    )
    rng.shuffle(picks)
    return picks[:N]


def main(live: bool = False) -> None:
    with open("datagen/out/dataset_test.json") as fh:
        test = json.load(fh)
    cases = sample(test)
    fixtures = json.loads(FIX.read_text()) if FIX.exists() else {}
    results, lat, tokens = [], [], [0]
    pending = [(i, c) for i, c in enumerate(cases) if case_key(c) not in fixtures]
    if pending and not live:
        raise SystemExit(f"{len(pending)} cases lack fixtures; rerun with --live")
    if pending:
        print(f"live calls needed: {len(pending)} (cap {N})")
        assert len(pending) <= N

        def _one(idx_case):
            idx, case = idx_case
            pack = llm_only(case, "live")
            sec = pack.pop("_seconds")
            return idx, case, pack, sec

        with ThreadPoolExecutor(max_workers=6) as ex:
            for idx, case, pack, sec in ex.map(_one, pending):
                fixtures[case_key(case)] = pack["decision"]
                tokens[0] += pack.pop("_tokens", 0)
                lat.append(sec)
                print(
                    f"[live {idx + 1}/{len(cases)}] {case['op']} "
                    f"got={pack['decision']['status']} {sec:.1f}s",
                    flush=True,
                )
        FIX.write_text(json.dumps(fixtures, indent=1))
    for i, case in enumerate(cases):
        d = fixtures[case_key(case)]
        pack = {
            "decision": {
                **d,
                "tier": d.get("tier") or "MEDIUM",
                "score": {"total": 50},
                "counterfactuals": [],
                "decision_id": None,
            },
            "findings": [],
            "run_id": None,
        }
        results.append(result_of(case, pack, 0.0))
    report = compute(results)
    report["E19_cost"] = {"tokens": tokens[0], "note": "25-case slice, live once"}
    report["meta"] = {"split": "test-25", "mode": "llm-only", "n": len(results)}
    (OUT / "ablation-llm-only-test25.json").write_text(
        json.dumps({"results": results, "metrics": report}, indent=1)
    )
    m = report
    print(
        f"E1={m['E1_critical_false_approve']} E3={m['E3_false_reject']} "
        f"E5={m['E5_status_accuracy']['rate']:.3f} tokens={tokens[0]}"
    )
    print("wrote eval/reports/ablation-llm-only-test25.json")


if __name__ == "__main__":  # pragma: no cover
    import sys

    main(live="--live" in sys.argv)
