# ADR 0009 — Approval route preview while vendor items remain open

## Context

Spec §9.S10 sets `route = approvers_for(tier)` only when PENDING(INTERNAL)
with no blocking findings. Phase 2 gate P2-G4 requires HP-3-HIGH to display
route [CONTROLLER, COMPLIANCE] while vendor-fixable blockers (missing COI,
justification) are still open. Derives from demo/explainability need.

## Decision

`decide()` populates `approval_route` whenever INTERNAL is in `awaiting`,
even with vendor blockers outstanding (approvers act after vendor fixes land).
LOW tier keeps the LOW_GATED `[AP_ANALYST]` route.

## Consequences

HP-3-HIGH and EC-3b goldens carry non-empty routes alongside vendor items.
No change to status/tier/score logic.

## Alternatives Considered

Keep spec-literal `route = []` under vendor blockers — rejected: hides the
dual-approval path the HIGH-tier demo must show.
