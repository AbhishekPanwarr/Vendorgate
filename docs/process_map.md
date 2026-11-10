# Process map (WP-00; mirrors solution §5.2)

```mermaid
flowchart TD
  IN(["Submission + documents"]) --> S0["S0 Intake & normalize (claims)"]
  S0 --> S1["S1 Document ingestion & extraction"]
  S0 --> S6["S6 Duplicate & network analysis"]
  S0 --> S7["S7 Risk screening"]
  S1 --> S2["S2 Completeness & applicability"]
  S1 --> S3["S3 Format & checksum validation"]
  S0 --> S3
  S3 --> S4["S4 External verification"]
  S1 --> S5["S5 Cross-field consistency"]
  S3 --> S5
  S4 --> S5
  S5 --> S8["S8 Gray-zone adjudication"]
  S7 --> S8
  S2 --> S9["S9 Risk scoring & tiering"]
  S6 --> S9
  S8 --> S9
  S9 --> S10["S10 Decision, routing, counterfactuals"]
  S10 --> S11["S11 Communications"]
  S11 --> S12["S12 Persist, audit, ERP outbox"]
  S12 --> OUT(["APPROVED / PENDING / REJECTED + case"])
```

| Stage | Input | Decision | Output |
|---|---|---|---|
| S0 | submission JSON + files | mode NEW/CHANGE | claims, diff |
| S1 | documents | type/extract/ground | doc claims |
| S2 | policy requirements | complete? | MISSING_* |
| S3 | IDs | format/checksum? | TAX_*/BANK_* |
| S4 | IDs | verifier verdict? | VER_* (or UNVERIFIABLE) |
| S5 | names/geo | consistent? | NAME_*/GEO_* |
| S6 | master index | duplicate? | DUP_* |
| S7 | lists | hit? | SAN_* |
| S8 | gray requests | adjudicate (bounded) | WARN or stands |
| S9 | tags + facts | score/tier | RiskBreakdown |
| S10 | findings | decide/route | Decision |
| S11 | decision | render/check | outbox messages |
| S12 | all | persist/chain | audit + ERP outbox |
| S13 | resubmit/clock | delta/scheduler | rerun subset |
