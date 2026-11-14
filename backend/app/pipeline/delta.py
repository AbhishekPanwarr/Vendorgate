"""Delta engine: changed-path diff + introduced/resolved detection."""

from typing import Any


def flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def changed_paths(old: dict[str, Any], new: dict[str, Any]) -> set[str]:
    a, b = flatten(old), flatten(new)
    changed = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
    # map indexed doc paths to the claim-style paths checks read
    mapped: set[str] = set()
    for p in changed:
        mapped.add(p)
        if p.startswith("documents["):
            mapped.add("documents.digest")
    return mapped


def _key(f: dict[str, Any]) -> tuple[str, str]:
    return (str(f.get("check_id", "")), str(f.get("subject") or ""))


def _blocking(f: dict[str, Any]) -> bool:
    return f.get("outcome") == "FAIL" or (
        f.get("outcome") == "UNVERIFIABLE" and f.get("mandatory", True)
    )


def compute_delta(
    old_findings: list[dict[str, Any]],
    new_findings: list[dict[str, Any]],
    changed: set[str],
    rerun: int,
    cached: int,
) -> dict[str, Any]:
    old_by_key = {_key(f): f for f in old_findings}
    new_by_key = {_key(f): f for f in new_findings}
    resolved = sorted(
        k[0] for k, f in old_by_key.items() if _blocking(f) and not _blocking(new_by_key.get(k, {}))
    )
    introduced = sorted(
        k[0]
        for k, f in new_by_key.items()
        if _blocking(f)
        and not _blocking(old_by_key.get(k, {}))
        and any(p in changed for p in (f.get("reads") or []))
    )
    return {"rerun": rerun, "cached": cached, "resolved": resolved, "introduced": introduced}
