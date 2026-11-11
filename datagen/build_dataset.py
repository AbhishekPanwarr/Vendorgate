"""Dataset builder: world vendors x operators -> cases with labels from catalog.

Labels come ONLY from catalog.yaml expected. This module must never import
the execution engine (see test_label_independence.py).
"""

import copy
import hashlib
import json
import random
from pathlib import Path

import yaml

from datagen.mutations.apply import OPS
from datagen.submissions import submission_for

OUT = Path("datagen/out")
SEED = 42

NEEDS_MASTER = {"M-26", "M-27", "M-28", "M-29", "M-37"}
# Doubles that silently break each other's preconditions (catalog conflicts_with
# is frozen; these are builder-level composition guards).
_TAX_IDS = {"M-04", "M-05", "M-06", "M-07", "M-14", "M-18", "M-19", "M-20",
            "M-26", "M-27", "M-28", "M-37"}
_NAME_DEP = {"M-26", "M-27", "M-29", "M-30", "M-31", "M-32", "M-41"}
_DOC_SURGERY = {"M-02", "M-03", "M-22", "M-23", "M-24", "M-25", "M-43", "M-44"}


def _conflicts(a, b):
    if a in _TAX_IDS and b in _TAX_IDS:
        return True
    if a in _NAME_DEP and b in _NAME_DEP:
        return True
    if a in _DOC_SURGERY and b in _DOC_SURGERY:
        return True
    return False
COUNTRY_OF = {"M-01": "IN", "M-04": "IN", "M-05": "IN", "M-06": "IN",
              "M-07": "IN", "M-20": "IN", "M-17": "US",
              "M-18": "US", "M-19": "US", "M-24": "US", "M-25": "US",
              "M-16": "GB"}


def _catalog():
    with open("datagen/mutations/catalog.yaml") as fh:
        return {o["id"]: o for o in yaml.safe_load(fh)["operators"]}


def _ctx():
    return {"files": {}, "l1": {}, "mocks": {}, "master": [], "sanctions": [],
            "pep": [], "adverse": [], "faults": {}, "l3": [], "setup_cases": []}


def _truth_mocks(ctx, vendor, payload):
    """Truth rows keyed by the PAYLOAD's current IDs; operator-set keys win."""
    c = payload["company"]["country"]
    tax_id = payload["tax"]["tax_id"]
    legal = payload["company"]["legal_name"]
    if c == "US":
        ctx["mocks"].setdefault(("irs", tax_id.replace("-", "")), {
            "status": "OK", "data": {"code": 0, "name": legal}})
    elif c == "IN":
        ctx["mocks"].setdefault(("gst", tax_id), {
            "status": "OK", "data": {"state": "Active", "legal_name": legal}})
    else:
        ctx["mocks"].setdefault(("vies", tax_id), {
            "status": "OK", "data": {"valid": True, "name": legal}})
    from backend.app.matching.normalize import canon_text

    key, _ = canon_text(payload["company"]["legal_name"])
    ctx["mocks"].setdefault(("registry", key), {
        "status": "OK",
        "data": {"status": "Active", "legal_name": legal,
                 "incorporation_year": vendor["truth"]["incorporation_year"],
                 "country": c, "officers": []}})
    b = payload["bank"]
    digits = "".join(ch for ch in str(b.get("account_number", "")) if ch.isdigit())
    if c == "US":
        acct = f"US|{b.get('routing_number')}|{digits}"
    elif c == "IN":
        acct = f"IN|{b.get('ifsc')}|{digits}"
    else:
        acct = f"{c}||{digits}"
    ctx["mocks"].setdefault(("bank", acct), {
        "status": "OK",
        "data": {"holder_name": vendor["legal_name"], "verified": True}})


def _l3_entries(payload):
    from backend.app.core.policy import load_policy
    from backend.app.llm.client import cache_key
    from backend.app.llm.tasks_l3 import adjudication_user
    from backend.app.llm.tasks_other import L3_SYSTEM, AdjudicationVerdict
    from backend.app.matching.name_compare import compare_names, parse_name

    from backend.app.matching.normalize import canon_text

    cfg = dict(load_policy("policy").raw["base"]["matching"]["name"])
    entries = []
    pairs = [(payload["company"]["legal_name"], payload["bank"]["account_holder_name"])]
    for a, b in pairs:
        # S8 sends claim (canonical) values, not raw payload strings
        ca, _ = canon_text(a)
        cb, _ = canon_text(b)
        rel = compare_names(parse_name(ca), parse_name(cb), cfg)
        label = {"EXACT": "SAME", "EQUIVALENT": "SAME", "FORM_CONFLICT": "SAME",
                 "CORE_FUZZY": "LIKELY_SAME"}.get(rel.relation, "DIFFERENT")
        conf = 0.9 if label == "SAME" else (0.75 if label == "LIKELY_SAME" else 0.8)
        det = {"core_similarity": rel.core_sim, "legal_form_relation": rel.form_rel}
        entries.append([ca, cb, payload["company"]["country"], det, label, conf])
    return entries


def _master_row(vendor):
    from backend.app.matching.normalize import canon_id, canon_text
    from backend.app.network.graph import bank_key

    b = vendor["bank"]
    c = vendor["country"]
    digits = "".join(ch for ch in str(b.get("account_number", "")) if ch.isdigit())
    routing = b.get("routing_number") or b.get("ifsc") or b.get("swift_bic") or ""
    core, _ = canon_text(vendor["legal_name"])
    from backend.app.validators.phone import validate_phone

    ph = validate_phone(vendor["phone"], c)
    phone = ph.normalized if ph.valid else vendor["phone"]
    return {"vendor_id": vendor["vendor_id"], "legal_name": vendor["legal_name"],
            "name_core": core,
            "tax_id": canon_id(vendor["tax"]["tax_id"]),
            "tax_id_raw": vendor["tax"]["tax_id"],
            "bank": bank_key(c, routing, digits),
            "account_number": b.get("account_number", ""),
            "routing_number": b.get("routing_number", ""),
            "ifsc": b.get("ifsc", ""), "phone": phone,
            "domain": vendor["email"].split("@")[1].lower()}


def _expected(op_id):
    e = _catalog()[op_id]["expected"]
    return {"status": e["status"], "awaiting": sorted(e["awaiting"]),
            "blocking_reason_codes": sorted(e["blocking_reason_codes"]),
            "critical": bool(e["critical"])}


def _render_files(ctx, p):
    from datagen.render_docs import doc_sha, l1_entry, render_pdf

    out, l1 = {}, {}
    declared = {d["doc_type"]: d["doc_id"] for d in p["documents"]}
    vals = _doc_values(p)
    for dtype, doc_id in declared.items():
        if dtype not in ("W9", "GST_CERT", "VAT_CERT", "INCORP_CERT",
                         "BANK_LETTER", "COI", "W8BEN"):
            continue
        pdf = render_pdf(dtype, vals.get(dtype, {}))
        out[doc_id] = [f"{dtype.lower()}.pdf", pdf.hex()]
        l1[(dtype, doc_id)] = l1_entry(dtype, vals.get(dtype, {}))
    ctx["l1_rendered"] = l1
    return out


def _doc_values(p):
    c = p["company"]["country"]
    tax = {"business_name": p["company"]["legal_name"],
           "tax_classification": "Limited Liability Company",
           "tin": p["tax"]["tax_id"], "signature_present": "/s/ Owner",
           "signature_date": "2026-10-01", "form_revision": "March 2024",
           "legal_name": p["company"]["legal_name"], "gstin": p["tax"]["tax_id"],
           "trade_name": p["company"]["legal_name"], "state": p["tax"]["tax_id"][:2],
           "registration_date": "2020-05-01", "status": "Active",
           "address": "x", "vat_id": p["tax"]["tax_id"],
           "effective_date": "2016-04-12", "registration_no": "1",
           "incorporation_date": p["company"]["incorporation_date"],
           "registered_address": "x",
           "account_holder": p["bank"]["account_holder_name"],
           "account_number": p["bank"].get("account_number") or "",
           "routing": p["bank"].get("routing_number") or p["bank"].get("ifsc") or "",
           "letter_date": "2026-09-15", "signatory": "Branch Manager",
           "insured_name": p["company"]["legal_name"], "insurer": "Test General",
           "policy_no": "GL-1", "expiry_date": "2027-06-01",
           "certificate_holder": "Buyer Corp",
           "name": p["company"]["legal_name"], "country": c}
    return {d: tax for d in ("W9", "GST_CERT", "VAT_CERT", "INCORP_CERT",
                             "BANK_LETTER", "COI", "W8BEN")}


def build_case(op_id, vendor, world, rng, with_files=True):
    ctx = _ctx()
    payload = submission_for(vendor)
    master = None
    if op_id in NEEDS_MASTER:
        pool = [v for v in world["vendors"]
                if v["vendor_id"] != vendor["vendor_id"]
                and v["country"] == vendor["country"]]
        m = rng.choice(pool)
        master = _master_row(m)
        ctx["master"].append(master)
    OPS[op_id](payload, vendor, world, rng, ctx, master)
    _truth_mocks(ctx, vendor, payload)
    if op_id == "M-38":
        ctx["master"].append({"vendor_id": "V-VEL-1", "legal_name": vendor["legal_name"],
                              "tax_id": vendor["tax"]["tax_id"],
                              "account_number": "0001", "routing_number": "",
                              "ifsc": "", "phone": "", "domain": ""})
        for i in range(2):
            sp = copy.deepcopy(payload)
            sp["submission_type"] = "CHANGE_REQUEST"
            sp["existing_vendor_id"] = "V-VEL-1"
            sp["bank"]["account_number"] = f"90000000000{i}"
            ctx["setup_cases"].append(sp)
    # files: operator-supplied custom docs win; render the rest
    files, l1, _deg = _merge_files(ctx, payload, op_id, rng)
    case = {"op": op_id, "vendor_id": vendor["vendor_id"], "payload": payload,
            "expected": _expected(op_id),
            "mocks": {f"{a}|{k}": v for (a, k), v in ctx["mocks"].items()},
            "master": ctx["master"],
            "sanctions": ctx["sanctions"], "pep": ctx["pep"],
            "adverse": ctx["adverse"], "faults": ctx["faults"],
            "setup_cases": ctx["setup_cases"],
            "l3": _l3_entries(payload),
            "files": files, "l1_rendered": l1, "degraded": _deg}
    return case


def _merge_files(ctx, payload, op_id, rng):
    """Custom operator docs preserved; remaining declared docs rendered.

    M-44 degrades the bank letter (no L1 entry: OCR path in eval).
    """
    from datagen.render_docs import degrade_pdf

    files, l1, degraded = {}, {}, {}
    for doc_id, (fn, pdf) in ctx["files"].items():
        files[doc_id] = [fn, pdf.hex() if isinstance(pdf, bytes) else pdf]
    rendered = _render_files(ctx, payload) if not files else {}
    for doc_id, (fn, hexpdf) in rendered.items():
        if doc_id not in files:
            files[doc_id] = [fn, hexpdf]
    for key, entry in ctx.get("l1_rendered", {}).items():
        l1[f"{key[0]}|{key[1]}"] = entry
    if op_id == "M-44":
        for doc_id, (fn, hexpdf) in list(files.items()):
            if fn == "bank.pdf":
                degraded[doc_id] = 1
                l1 = {k: v for k, v in l1.items() if not k.startswith("BANK_LETTER|")}
    # ctx["l1"] entries from operators (custom docs) keyed (dtype, doc_id);
    # values are either entry dicts or (entry, pdf) tuples
    for (dtype, doc_id), val in ctx["l1"].items():
        entry = val[0] if isinstance(val, tuple) else val
        l1[f"{dtype}|{doc_id}"] = entry
    return files, l1, degraded


def _pick(world, rng, country=None):
    pool = [v for v in world["vendors"]
            if (country is None or v["country"] == country) and "-B" not in v["vendor_id"]]
    return rng.choice(pool)


def build_dataset(seed=SEED):
    rng = random.Random(seed)
    with open("datagen/out/world.json") as fh:
        world = json.load(fh)
    catalog = _catalog()
    op_ids = sorted(catalog.keys())
    cases = []
    for v in world["vendors"]:
        c = _clean(v, world, rng)
        cases.append(("clean", c))
    for i in range(240):
        op = op_ids[i % len(op_ids)]
        cases.append(("single", _op_case(op, world, rng)))
    for i in range(100):
        a, b = rng.sample(op_ids, 2)
        cat = catalog
        if (b in cat[a].get("conflicts_with", [])
                or a in cat[b].get("conflicts_with", []) or _conflicts(a, b)):
            for _ in range(20):
                b = rng.choice(op_ids)
                if not (b in cat[a].get("conflicts_with", [])
                        or a in cat[b].get("conflicts_with", [])
                        or _conflicts(a, b)):
                    break
            else:
                b = "M-45"
        cases.append(("double", _double_case(a, b, world, rng)))
    # scanned: degraded OCR path; sample ONLY APPROVED-expected cases
    # (freshness findings need L1 ground truth, absent on the OCR path)
    scan_pool = [c for c in cases
                 if c[0] in ("clean", "single") and c[1]["expected"]["status"] == "APPROVED"]
    for sl, case in rng.sample(scan_pool, 60):
        sc = copy.deepcopy(case)
        sc.setdefault("degraded", {})
        for doc_id, (fn, hexpdf) in list(sc["files"].items()):
            if fn == "bank.pdf":
                sc["degraded"][doc_id] = 7
                sc["l1_rendered"] = {k: v for k, v in sc["l1_rendered"].items()
                                     if not k.startswith("BANK_LETTER|")}
        cases.append(("scanned", sc))
    # adversarial: hand-built tricky cases
    for op in (["M-43"] * 10 + ["M-41"] * 10 + ["M-27"] * 10 + ["M-32"] * 10):
        cases.append(("adversarial", _op_case(op, world, rng)))
    return cases


def _clean(vendor, world, rng):
    ctx = _ctx()
    payload = submission_for(vendor, spend=3000)
    payload["requester"]["category"] = "OFFICE_SUPPLIES"
    _truth_mocks(ctx, vendor, payload)
    case = {"op": None, "vendor_id": vendor["vendor_id"], "payload": payload,
            "expected": {"status": "APPROVED", "awaiting": [],
                         "blocking_reason_codes": [], "critical": False},
            "mocks": {f"{a}|{k}": v for (a, k), v in ctx["mocks"].items()},
            "master": [], "sanctions": [], "pep": [], "adverse": [],
            "faults": {}, "setup_cases": [], "l3": _l3_entries(payload)}
    case["files"] = _render_files(ctx, payload)
    case["l1_rendered"] = {f"{a}|{b}": v for (a, b), v in ctx["l1_rendered"].items()}
    case["degraded"] = {}
    return case


def _op_case(op_id, world, rng):
    country = COUNTRY_OF.get(op_id)
    vendor = _pick(world, rng, country)
    return build_case(op_id, vendor, world, rng)


def _double_case(a, b, world, rng):
    vendor = _pick(world, rng, COUNTRY_OF.get(a) or COUNTRY_OF.get(b))
    ctx = _ctx()
    payload = submission_for(vendor)
    master = None
    if a in NEEDS_MASTER or b in NEEDS_MASTER:
        pool = [v for v in world["vendors"]
                if v["vendor_id"] != vendor["vendor_id"]
                and v["country"] == vendor["country"]]
        m = rng.choice(pool)
        master = _master_row(m)
        ctx["master"].append(master)
    OPS[a](payload, vendor, world, rng, ctx, master)
    OPS[b](payload, vendor, world, rng, ctx, master)
    _truth_mocks(ctx, vendor, payload)
    ea, eb = _expected(a), _expected(b)
    order = {"APPROVED": 0, "PENDING": 1, "REJECTED": 2}
    worse = ea if order[ea["status"]] >= order[eb["status"]] else eb
    case = {"op": [a, b], "vendor_id": vendor["vendor_id"], "payload": payload,
            "expected": {"status": worse["status"],
                         "awaiting": sorted(set(ea["awaiting"]) | set(eb["awaiting"])),
                         "blocking_reason_codes": sorted(
                             set(ea["blocking_reason_codes"]) | set(eb["blocking_reason_codes"])),
                         "critical": ea["critical"] or eb["critical"]},
            "mocks": {f"{a_}|{k}": v for (a_, k), v in ctx["mocks"].items()},
            "master": ctx["master"], "sanctions": ctx["sanctions"],
            "pep": ctx["pep"], "adverse": ctx["adverse"], "faults": ctx["faults"],
            "setup_cases": ctx["setup_cases"], "l3": _l3_entries(payload)}
    files, l1, _ddeg = _merge_files(ctx, payload, [a, b], rng)
    case["files"] = files
    case["l1_rendered"] = l1
    case["degraded"] = _ddeg
    return case


def main(seed=SEED) -> None:
    cases = build_dataset(seed)
    OUT.mkdir(parents=True, exist_ok=True)
    by_slice: dict[str, list] = {}
    for sl, case in cases:
        by_slice.setdefault(sl, []).append(case)
    # dev 60 / test 40 stratified by op
    dev, test = [], []
    rng = random.Random(seed + 1)
    groups: dict[str, list] = {}
    for sl, case in cases:
        op = case["op"]
        key = (sl, str(op)) if sl != "double" else (sl, "any")
        groups.setdefault(key, []).append((sl, case))
    for key, items in groups.items():
        if key[0] == "adversarial":
            for sl, case in items:
                test.append(case)
            continue
        rng.shuffle(items)
        n_test = max(1, int(len(items) * 0.4)) if len(items) > 2 else 0
        for sl, case in items[: len(items) - n_test]:
            dev.append(case)
        for sl, case in items[len(items) - n_test:]:
            test.append(case)
    blob_dev = json.dumps(dev, sort_keys=True)
    blob_test = json.dumps(test, sort_keys=True)
    (OUT / "dataset_dev.json").write_text(blob_dev)
    (OUT / "dataset_test.json").write_text(blob_test)
    manifest = {
        "seed": seed,
        "counts": {sl: len(v) for sl, v in by_slice.items()},
        "dev": len(dev), "test": len(test),
        "test_split_sha256": hashlib.sha256(blob_test.encode()).hexdigest(),
        "dataset_sha256": hashlib.sha256((blob_dev + blob_test).encode()).hexdigest(),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"dataset: dev={len(dev)} test={len(test)} "
          f"split={manifest['test_split_sha256'][:12]}")


if __name__ == "__main__":
    import sys

    seed = int(sys.argv[sys.argv.index("SEED") + 1]) if "SEED" in sys.argv else SEED
    main(seed)
