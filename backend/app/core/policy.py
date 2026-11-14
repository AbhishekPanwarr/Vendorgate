"""Policy loader. version = sha256(canonical_json(parsed YAML))."""

from pathlib import Path
from typing import Any

import yaml

from backend.app.core.hashing import canonical_json
from backend.app.core.hashing import sha256_hex
from backend.app.domain.models import Finding


class Policy:
    raw: dict[str, Any]
    version: str

    def __init__(self, raw: dict[str, Any], version: str) -> None:
        self.raw = raw
        self.version = version

    def hash_for(self, check_id: str) -> str:
        from backend.app.core.hashing import canonical_json as cj
        from backend.app.core.hashing import sha256_hex as sh

        slice_ = {"version": self.version, "check": check_id}
        base = self.raw.get("base", {})
        for key in ("scoring", "matching", "approvals", "lifecycle"):
            if key in base:
                slice_[key] = base[key]
        return sh(cj(slice_))

    def weight(self, component: str) -> float:
        return float(self.raw["base"]["scoring"]["weights"][component])

    def is_blocking(self, finding: Finding) -> bool:
        from backend.app.domain.enums import Outcome

        if finding.outcome == Outcome.FAIL:
            return True
        if finding.outcome == Outcome.UNVERIFIABLE and finding.mandatory:
            return True
        return False

    def requirements(
        self, country: str, entity_type: str, category: str, tier: str, submission_type: str
    ) -> dict[str, Any]:
        packs = self.raw.get("countries", {})
        return dict(packs.get(country, {"fields": [], "docs": [], "conditional": []}))


def load_policy(policy_dir: str | Path = "policy") -> Policy:
    base_p = Path(policy_dir)
    docs: list[Any] = []
    files = [base_p / "base.yaml"]
    files += sorted((base_p / "countries").glob("*.yaml"))
    files += [base_p / "legal_forms.yaml", base_p / "fix_hints.yaml"]
    for f in files:
        with open(f) as fh:
            docs.append(yaml.safe_load(fh))
    version = sha256_hex(canonical_json(docs))
    countries: dict[str, Any] = {}
    for f in sorted((base_p / "countries").glob("*.yaml")):
        with open(f) as fh:
            data = yaml.safe_load(fh)
            countries[data.get("country", f.stem)] = data.get("requirements", {})
    with open(base_p / "base.yaml") as fh:
        base = yaml.safe_load(fh)
    raw = {"base": base, "countries": countries}
    return Policy(raw=raw, version=version)
