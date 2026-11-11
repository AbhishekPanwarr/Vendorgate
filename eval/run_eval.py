"""run_eval: dataset split x mode -> results JSON + metric report.

Modes: hybrid (full engine), rules-only (LLM off), llm-only (single-call baseline).
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

from eval.case_runner import run_case
from eval.metrics import compute

OUT = Path("eval/reports")


def load_split(split: str) -> list[dict]:
    with open(f"datagen/out/dataset_{split}.json") as fh:
        return json.load(fh)


def check_frozen(split: str) -> None:
    with open("datagen/out/manifest.json") as fh:
        manifest = json.load(fh)
    with open(f"datagen/out/dataset_{split}.json", "rb") as fh:
        blob = fh.read()
    digest = hashlib.sha256(blob).hexdigest()
    if split == "test" and digest != manifest["test_split_sha256"]:
        raise SystemExit(
            f"test split changed (manifest {manifest['test_split_sha256'][:12]} "
            f"!= file {digest[:12]}); refusing --split test")


def result_of(case: dict, pack: dict, seconds: float) -> dict:
    dec = pack["decision"]
    findings = pack.get("findings", [])
    blocking = [f for f in findings
                if f.get("outcome") == "FAIL" and f.get("severity", 0) >= 1]
    has_cf = bool(dec.get("counterfactuals"))
    exp = case["expected"]
    status = str(dec["status"]).upper()
    if status not in ("APPROVED", "PENDING", "REJECTED"):
        status = "ERROR"
    awaiting = [a for a in (str(x).upper() for x in dec.get("awaiting", []))
                if a in ("VENDOR", "INTERNAL")]
    return {
        "op": case["op"], "vendor_id": case["vendor_id"],
        "slice": case.get("slice"),
        "expected_status": exp["status"],
        "expected_awaiting": exp["awaiting"],
        "expected_codes": exp["blocking_reason_codes"],
        "expected_critical": exp["critical"],
        "actual_status": status,
        "actual_awaiting": awaiting,
        "actual_codes": dec.get("reason_codes", []),
        "tier": dec.get("tier"), "score": dec.get("score", {}).get("total", 0),
        "has_counterfactual": has_cf,
        "has_audit": bool(dec.get("decision_id") or pack.get("run_id")),
        "n_blocking": len(blocking),
        "seconds": round(seconds, 2),
    }


def llm_only(case: dict, llm_mode: str) -> dict:
    """Single-call baseline: submission -> status + codes (fair schema)."""
    import os

    from backend.app.llm.factory import llm_model, make_llm
    from backend.app.llm.tasks_other import LlmOnlyVerdict, LLM_ONLY_SYSTEM, llm_only_user

    os.environ["LLM_MODE"] = llm_mode
    llm = make_llm(store={})
    import asyncio

    payload = json.dumps(case["payload"], default=str)[:12000]
    t0 = time.time()
    last = None
    out = None
    for _ in range(3):
        try:
            out = asyncio.run(llm.structured(
                task="llm-only baseline", model=llm_model(), system=LLM_ONLY_SYSTEM,
                user=llm_only_user(payload), schema=LlmOnlyVerdict, max_tokens=4096))
            break
        except Exception as e:  # noqa: BLE001 - baseline must not crash eval
            last = e
    if out is None:
        out = LlmOnlyVerdict(status="ERROR", awaiting=[],
                             reason_codes=["BASELINE_ERROR"],
                             rationale=f"3 attempts failed: {last}")
    tokens = int(getattr(out, "_tokens_used", 0) or 0)
    return {"decision": {"status": out.status,
                         "awaiting": out.awaiting,
                         "reason_codes": out.reason_codes,
                         "tier": "MEDIUM",
                         "score": {"total": 50},
                         "counterfactuals": [],
                         "decision_id": None},
            "findings": [], "run_id": None,
            "_seconds": round(time.time() - t0, 2),
            "_tokens": tokens}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--mode", choices=["hybrid", "rules-only", "llm-only"],
                    required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--llm-mode", default="replay")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    from eval.ablation import run_mode as _run_mode

    data = _run_mode(args.mode, args.split, args.limit, args.llm_mode,
                     offset=args.offset)
    OUT.mkdir(parents=True, exist_ok=True)
    name = args.out or f"{args.split}-{args.mode}-latest.json"
    (OUT / name).write_text(json.dumps({"results": data["results"],
                                        "metrics": data["metrics"]}, indent=1))
    print(f"wrote eval/reports/{name}")
    m = data["metrics"]
    print(f"E1={m['E1_critical_false_approve']} E3={m['E3_false_reject']} "
          f"E5={m['E5_status_accuracy']['rate']:.3f}")


