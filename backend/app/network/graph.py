"""Vendor master index + entity graph (dedupe)."""

import hashlib
import os
from typing import Any

import networkx as nx

SALT = os.environ.get("BANK_HASH_SALT", "dev-salt")
# NOTE: salt rotation invalidates the index (Phase 5+ concern, see decisions.md).

# Seeded master (hand fixtures; Phase 5 generates from truth store).
VENDORS: dict[str, dict[str, Any]] = {}

# Per-case overlay for eval/fool-it (extra master rows for this case only).
_EXTRA_VENDORS: dict[str, dict[str, Any]] = {}


def _all_vendors() -> dict[str, dict[str, Any]]:
    merged = dict(VENDORS)
    merged.update(_EXTRA_VENDORS)
    return merged


def bank_key(country: str, routing: str, account: str) -> str:
    raw = f"{country}|{routing}|{account}|{SALT}"
    return "BANK:" + hashlib.sha256(raw.encode()).hexdigest()[:32]


def seed_master() -> None:
    VENDORS.clear()
    VENDORS.update(
        {
            "V-000044": {
                "vendor_id": "V-000044",
                "legal_name": "Helios Freight Pvt Ltd",
                "name_core": "helios freight",
                "tax_id": "29HELIOS000F1Z5",
                "bank": bank_key("IN", "HDFC0001234", "987654321098"),
                "phone": "+919876543210",
                "domain": "helios-freight.example",
            },
            "V-000017": {
                "vendor_id": "V-000017",
                "legal_name": "Beacon Retail Group Inc",
                "name_core": "beacon retail group",
                "tax_id": "52-7654321",
                "bank": bank_key("US", "021000021", "111222333444"),
                "phone": "+16145550100",
                "domain": "beacon-retail.example",
                "bank_phones": ["+16145550100"],
            },
        }
    )


def attr_keys(attrs: dict[str, Any]) -> dict[str, str]:
    return {k: v for k, v in attrs.items() if v}


def find_bank_reuse(bkey: str, exclude: str | None = None) -> list[dict[str, Any]]:
    return [v for vid, v in _all_vendors().items() if v.get("bank") == bkey and vid != exclude]


def find_tin_reuse(tin: str, exclude: str | None = None) -> list[dict[str, Any]]:
    return [v for vid, v in _all_vendors().items() if v.get("tax_id") == tin and vid != exclude]


def build_graph(cases: list[dict[str, Any]]) -> nx.Graph:
    g = nx.Graph()
    nodes: dict[str, dict[str, Any]] = {}
    for v in list(_all_vendors().values()) + cases:
        vid = v.get("vendor_id") or v.get("case_id", "case")
        nodes[vid] = v
        g.add_node(vid, kind="vendor")
    for attr in ("phone", "domain"):
        buckets: dict[str, list[str]] = {}
        for vid, v in nodes.items():
            val = v.get(attr)
            if val:
                buckets.setdefault(str(val), []).append(vid)
        for val, vids in buckets.items():
            if len(vids) > 1:
                anode = f"{attr}:{val}"
                g.add_node(anode, kind="attr")
                for vid in vids:
                    g.add_edge(vid, anode)
    return g
