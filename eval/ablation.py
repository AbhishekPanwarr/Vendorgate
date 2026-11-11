"""Ablation runner: 7 modes x dataset split -> comparison table."""

import argparse
import json
import os
from pathlib import Path

from eval.metrics import compute

OUT = Path("eval/reports")

MODES = {
    "hybrid": {},
    "rules-only": {"llm": "off"},
    "llm-only": {"llm_only": True},
    "-corroboration": {"env": {"CORROB_OFF": "1"}},
    "-fail-closed": {"env": {"FAILOPEN": "1"}},
    "-network": {"env": {"NO_NETWORK": "1"}},
    "-counterfactual": {"env": {"NO_COUNTERFACTUAL": "1"}},
}


def run_mode(mode: str, split: str, limit: int, llm_mode: str, offset: int = 0) -> dict:
    from eval.case_runner import run_case
    from eval.run_eval import check_frozen, load_split, result_of

    check_frozen(split)
    cases = load_split(split)
    if offset:
        cases = cases[offset:]
    if limit:
        cases = cases[:limit]
    cfg = MODES[mode]
    old = dict(os.environ)
    try:
        os.environ.update(cfg.get("env", {}))
        if mode == "rules-only":
            llm_mode = "off"
        results = []
        import time

        lat = []
        tokens = [0]
        if cfg.get("llm_only"):
            from concurrent.futures import ThreadPoolExecutor

            from eval.run_eval import llm_only

            def _one(idx_case):
                idx, case = idx_case
                pack = llm_only(case, llm_mode)
                sec = pack.pop("_seconds")
                tokens[0] += pack.pop("_tokens", 0)
                r = result_of(case, pack, sec)
                print(
                    f"[{mode} {idx + 1}/{len(cases)}] {case['op']} "
                    f"exp={r['expected_status']} got={r['actual_status']}",
                    flush=True,
                )
                return sec, r

            with ThreadPoolExecutor(max_workers=6) as ex:
                for sec, r in ex.map(_one, enumerate(cases)):
                    lat.append(sec)
                    results.append(r)
        else:
            for i, case in enumerate(cases):
                t0 = time.time()
                pack = run_case(case, llm_mode=llm_mode)
                sec = round(time.time() - t0, 2)
                lat.append(sec)
                r = result_of(case, pack, sec)
                results.append(r)
                print(
                    f"[{mode} {i + 1}/{len(cases)}] {case['op']} "
                    f"exp={r['expected_status']} got={r['actual_status']} {sec:.1f}s"
                )
    finally:
        os.environ.clear()
        os.environ.update(old)
    import statistics

    report = compute(results)
    report["E18_latency"] = {
        "p50": round(statistics.median(lat), 2),
        "p95": round(sorted(lat)[max(0, int(len(lat) * 0.95) - 1)], 2),
        "mode": mode,
    }
    report["E19_cost"] = {
        "tokens": tokens[0],
        "note": "live baseline tokens" if tokens[0] else "replay/off",
    }
    report["meta"] = {"split": split, "mode": mode, "n": len(results)}
    return {"results": results, "metrics": report}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--llm-mode", default="replay")
    args = ap.parse_args()
    table = {}
    for mode in args.modes.split(","):
        data = run_mode(mode.strip(), args.split, args.limit, args.llm_mode)
        (OUT / f"ablation-{mode.strip().lstrip('-') or 'hybrid'}-{args.split}.json").write_text(
            json.dumps(data, indent=1)
        )
        m = data["metrics"]
        table[mode] = {
            "E1": m["E1_critical_false_approve"],
            "E3": m["E3_false_reject"],
            "E5": round(m["E5_status_accuracy"]["rate"], 4),
            "E6_f1": round(m["E6_reason_codes"]["micro"]["f1"], 4),
            "p95": m["E18_latency"]["p95"],
        }
    (OUT / f"ablation-{args.split}.json").write_text(json.dumps(table, indent=1))
    print(json.dumps(table, indent=1))


if __name__ == "__main__":  # pragma: no cover
    main()
