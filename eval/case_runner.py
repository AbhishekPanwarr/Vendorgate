"""Run a dataset case through the real execution engine with its side-fixtures."""

import asyncio
import binascii
import os

from backend.app.adapters.mocks import mockbase
from backend.app.adapters import faults as _faults
from backend.app.llm import client as llm_client
from backend.app.llm.factory import llm_model, make_llm
from backend.app.llm.tasks_extract import L1_SYSTEM, SCHEMAS
from backend.app.llm.tasks_l1 import user_text
from backend.app.network import graph
from backend.app.persistence import repo
from backend.app.pipeline.pipeline import run_full
from backend.app.screening import sanctions


def l1_key(dtype, pages):
    schema = SCHEMAS.get(dtype)
    if schema is None:
        from backend.app.llm.tasks_extract import GenericExtraction

        schema = GenericExtraction
    return llm_client.cache_key(llm_model(), L1_SYSTEM, user_text(dtype, pages), schema)


def build_store(case, files):
    from backend.app.ingest.text import extract_text_layer

    store = {}
    for doc_id, (fn, raw) in files.items():
        l1key = f"{_dtype_of(case, doc_id)}|{doc_id}"
        entry = case.get("l1_rendered", {}).get(l1key)
        if entry:
            pages, _ = extract_text_layer(raw)
            pages = [p for p in pages if p.strip()]
            store[l1_key(_dtype_of(case, doc_id), pages)] = entry
    for item in case.get("l3", []):
        a, b, country, det, label, conf = item
        from backend.app.llm.tasks_l3 import adjudication_user
        from backend.app.llm.tasks_other import L3_SYSTEM, AdjudicationVerdict

        for swap in (False, True):
            x, y = (a, b) if not swap else (b, a)
            sa, sb = ("form", "bank") if not swap else ("bank", "form")
            u = adjudication_user(x, sa, y, sb, country, det)
            key = llm_client.cache_key(llm_model(), L3_SYSTEM, u, AdjudicationVerdict)
            store[key] = {"label": label, "confidence": conf,
                          "rationale": "dataset fixture",
                          "order_swap_consistent": True}
    return store


def install_overlays(case):
    for k, v in case.get("mocks", {}).items():
        adapter, key = k.split("|", 1)
        mockbase._OVERLAY[(adapter, key)] = v
    graph._EXTRA_VENDORS.clear()
    for row in case.get("master", []):
        graph._EXTRA_VENDORS[row["vendor_id"]] = row
    sanctions._EXTRA_SANCTIONS[:] = case.get("sanctions", [])
    sanctions._EXTRA_PEP[:] = case.get("pep", [])
    sanctions._EXTRA_ADVERSE[:] = case.get("adverse", [])
    for adapter, mode in case.get("faults", {}).items():
        _faults.set_fault(adapter, mode)


def _dtype_of(case, doc_id):
    for d in case["payload"]["documents"]:
        if d["doc_id"] == doc_id:
            return d["doc_type"]
    return "BANK_LETTER"


def files_of(case):
    return {doc_id: (fn, binascii.unhexlify(hexpdf))
            for doc_id, (fn, hexpdf) in case.get("files", {}).items()}


def clear():
    mockbase._OVERLAY.clear()
    graph._EXTRA_VENDORS.clear()
    sanctions._EXTRA_SANCTIONS.clear()
    sanctions._EXTRA_PEP.clear()
    sanctions._EXTRA_ADVERSE.clear()
    _faults.clear_faults()


def run_case(case, mode="hybrid", llm_mode="replay"):
    os.environ["LLM_MODE"] = llm_mode
    repo.reset_store()
    try:
        install_overlays(case)
        for i, setup in enumerate(case.get("setup_cases", [])):
            llm = make_llm(store={})
            asyncio.run(run_full(setup, files={}, llm=llm, case_id=f"setup{i}"))
        install_overlays(case)
        files = files_of(case)
        store = build_store(case, files)
        llm = make_llm(store=store)
        return asyncio.run(run_full(case["payload"], files=files, llm=llm,
                                    case_id="eval"))
    finally:
        clear()
