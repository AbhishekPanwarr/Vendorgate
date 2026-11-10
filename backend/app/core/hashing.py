"""Canonical JSON + fingerprint (contract-critical)."""

import hashlib
import json
import unicodedata
from typing import Any
from typing import Mapping


def canonical_json(obj: Any) -> str:
    def norm(o: Any) -> Any:
        if isinstance(o, str):
            return unicodedata.normalize("NFC", o)
        if isinstance(o, dict):
            return {k: norm(o[k]) for k in sorted(o.keys())}
        if isinstance(o, (list, tuple)):
            return [norm(x) for x in o]
        return o

    return json.dumps(norm(obj), separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def fingerprint(
    *,
    check_id: str,
    version: int,
    subject: str | None,
    policy_hash: str,
    reads: Mapping[str, Any],
    adapters: Mapping[str, str],
    lists: Mapping[str, str],
) -> str:
    payload = {
        "check": check_id,
        "v": version,
        "subject": subject,
        "policy": policy_hash,
        "reads": dict(sorted(reads.items())),
        "adapters": dict(sorted(adapters.items())),
        "lists": dict(sorted(lists.items())),
    }
    return sha256_hex(canonical_json(payload))
