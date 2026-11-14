from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

from backend.app.domain.enums import Awaiting
from backend.app.domain.enums import DocType
from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.enums import Source
from backend.app.domain.enums import Status
from backend.app.domain.enums import Tier


class Claim(BaseModel):
    id: str
    path: str
    raw: str | None = None
    value: str | None = None
    source: Source
    doc_id: str | None = None
    page: int | None = None
    quote: str | None = None
    confidence: float = 1.0


class Evidence(BaseModel):
    kind: Literal["claim", "rule", "adapter", "llm", "policy"]
    ref: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)


class FixAction(BaseModel):
    code: str
    field_paths: list[str] = Field(default_factory=list)
    doc_type: DocType | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    check_id: str
    stage: str
    check_version: int
    subject: str | None = None
    outcome: Outcome
    severity: Severity = Severity.INFO
    reason_code: str | None = None
    title: str
    detail: str
    evidence: list[Evidence] = Field(default_factory=list)
    fix: FixAction | None = None
    fixed_by: FixedBy = FixedBy.NONE
    mandatory: bool = True
    deterministic: bool = True
    reads: list[str] = Field(default_factory=list)
    fingerprint: str = ""
    score_tags: dict[str, float] = Field(default_factory=dict)
    duration_ms: int = 0
    cached: bool = False

    @model_validator(mode="after")
    def _validate_evidence(self) -> "Finding":
        if self.outcome in (Outcome.FAIL, Outcome.WARN, Outcome.UNVERIFIABLE):
            if not self.evidence:
                raise ValueError("FAIL/WARN/UNVERIFIABLE requires non-empty evidence")
        if self.outcome == Outcome.FAIL and self.reason_code is None:
            raise ValueError("FAIL requires reason_code")
        return self


class ComponentScore(BaseModel):
    weight: float
    raw: float
    points: float
    drivers: list[str] = Field(default_factory=list)


class RiskBreakdown(BaseModel):
    components: dict[str, ComponentScore]
    total: float
    band: Tier

    @model_validator(mode="after")
    def _validate_total(self) -> "RiskBreakdown":
        if not 0 <= self.total <= 100:
            raise ValueError("total must be in [0,100]")
        return self


class Counterfactual(BaseModel):
    fix_set: list[str]
    status: Status
    tier: Tier
    score: float
    awaiting: set[Awaiting] = Field(default_factory=set)
    note: str = "assumes no new issues are found"
    score_delta: float | None = None


class Decision(BaseModel):
    status: Status
    awaiting: set[Awaiting] = Field(default_factory=set)
    tier: Tier
    score: RiskBreakdown
    reason_codes: list[str] = Field(default_factory=list)
    blocking_finding_ids: list[str] = Field(default_factory=list)
    required_actions: list[FixAction] = Field(default_factory=list)
    approval_route: list[str] = Field(default_factory=list)
    counterfactuals: list[Counterfactual] = Field(default_factory=list)
    policy_version: str
    engine_version: str
    reproducibility_hash: str

    @model_validator(mode="after")
    def _validate_awaiting(self) -> "Decision":
        if self.status == Status.APPROVED and self.awaiting:
            raise ValueError("APPROVED must have empty awaiting")
        return self


class Resolution(BaseModel):
    case_id: str
    finding_key: str
    action: Literal["CLEARED", "CONFIRMED"]
    role: str
    actor: str
    note: str
    at: str
