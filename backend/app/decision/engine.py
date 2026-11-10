"""Decision stub (Phase 1 implements)."""

from backend.app.domain.models import Counterfactual
from backend.app.domain.models import Decision
from backend.app.domain.models import Finding
from backend.app.domain.models import Resolution


def apply_resolutions(findings: list[Finding], resolutions: list[Resolution]) -> list[Finding]:
    raise NotImplementedError("Phase 1")


def decide(
    *,
    findings: list[Finding],
    resolutions: list[Resolution],
    submission_facts: object,
    policy: object,
) -> Decision:
    raise NotImplementedError("Phase 1")


def counterfactuals(*args: object, **kwargs: object) -> list[Counterfactual]:
    raise NotImplementedError("Phase 1")
