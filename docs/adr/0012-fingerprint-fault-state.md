# ADR 0012 — Adapter fault state participates in check fingerprints

## Context

Phase 4 chaos testing caught a stale cross-test cache hit: a C-VER check
that passed while its adapter was healthy was served from `check_cache`
after the adapter was faulted, because `fingerprint()` covered check
version + policy slice + reads + adapter versions but not fault state.
A cached PASS served during an outage breaks fail-closed semantics.

## Decision

The orchestrator passes per-adapter fault modes in the fingerprint `lists`
argument (`fault:{adapter} -> mode`). The frozen `fingerprint()` function
itself is unchanged; only its inputs grew. Effect: cache entries are
fault-state-scoped.

## Consequences

Cache size grows with fault combinations (bounded: only faulted adapters
differ). E15 determinism holds only with a fixed fault policy per run;
chaos tests set/clear faults explicitly. S10 checks bypass cache entirely
(they read other findings, which fingerprints cannot capture).

## Alternatives Considered

Per-check fault-awareness (each check re-validates adapter health on a hit)
— rejected: requires every check to know about fault state; the fingerprint
already carries equivalent information.
