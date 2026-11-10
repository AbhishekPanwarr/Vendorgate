"""Concrete RunContext: claims store + claim resolver + collaborators."""

from collections.abc import Callable
from collections.abc import Mapping
from typing import Any

from backend.app.adapters.base import Verifier
from backend.app.core.clock import Clock
from backend.app.core.policy import Policy
from backend.app.domain.models import Claim
from backend.app.domain.models import Finding
from backend.app.domain.submission import VendorSubmission


class CheckCache:
    def __init__(self) -> None:
        self._store: dict[str, list[Finding]] = {}

    def get(self, fp: str) -> list[Finding] | None:
        return self._store.get(fp)

    def put(self, fp: str, findings: list[Finding]) -> None:
        self._store[fp] = findings


class RunContext:
    def __init__(
        self,
        case_id: str,
        run_id: str,
        submission: VendorSubmission,
        policy: Policy,
        adapters: Mapping[str, Verifier[Any, Any]],
        llm: Any,
        clock: Clock,
        cache: CheckCache,
        emit: Callable[[dict[str, object]], None],
    ) -> None:
        self.case_id = case_id
        self.run_id = run_id
        self.submission = submission
        self.policy = policy
        self.adapters = adapters
        self.llm = llm
        self.clock = clock
        self.cache = cache
        self.emit = emit
        self.claims: dict[str, Claim] = {}  # noqa: F841
        self.findings: list[Finding] = []
        self.mode = submission.submission_type.value

    def add_claim(self, claim: Claim) -> None:
        self.claims[claim.path] = claim

    def value(self, path: str) -> Any:
        if path in self.claims:
            return self.claims[path].value
        node: Any = self.submission.model_dump()
        for part in path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None
        return node
