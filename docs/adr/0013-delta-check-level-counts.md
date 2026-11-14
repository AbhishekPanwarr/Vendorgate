# ADR 0013 — Delta stats are check-level, not finding-level

## Context

Phase 4's delta engine first counted `rerun`/`cached` over findings, which
undercounts: checks that re-execute but emit zero findings (the common
PASS-with-no-findings case) were invisible, producing claims like
"rerun 0, cached 3" for a resubmit that actually re-ran a dozen checks.

## Decision

`ctx.rerun_checks` / `ctx.cached_checks` record every executed check ID in
the orchestrator (hit branch appends once per check, not per finding).
`compute_delta` reports check-level counts; finding-level resolved /
introduced lists are unchanged.

## Consequences

The demo claim for EC-1-delta is "rerun 12, cached 36" (check-level), not
the brief's finding-level estimate (~4/~15). The video script must use the
check-level number. Golden `delta` objects carry the check-level counts.

## Alternatives Considered

Finding-level counts — rejected: systematically undercounts re-execution
and would make the demo claim false.
