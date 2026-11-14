# Assumptions (A-01..A-15, verbatim from solution §2.1)

| ID | Assumption |
|---|---|
| A-01 | Buyer is a mid-size company onboarding dozens of vendors per quarter; single tenant. |
| A-02 | Supported jurisdictions: US, IN, GB, DE. Adding a jurisdiction = policy pack + validators. |
| A-03 | All external verifiers are mocked behind production-shaped interfaces; fixtures deterministic. |
| A-04 | Sanctions list is fictional (plus generic embargoed ISO codes). |
| A-05 | Thresholds are illustrative, tuned on dev split only. |
| A-06 | Amounts converted to USD with static FX. |
| A-07 | Vendor portal identity is a simulated magic link. |
| A-08 | Email simulated by outbox table (optional SMTP sink). |
| A-09 | Documents synthetic, watermarked SYNTHETIC. |
| A-10 | Time controlled by virtual clock. |
| A-11 | ERP sync is a simulated outbox. |
| A-12 | Roles simulated by switcher; SoD enforced in code. |
| A-13 | Bank callback simulated by attestation; independence validated. |
| A-14 | 1099 threshold config ($2,000 post-2025; re-verify). |
| A-15 | Manual-review baseline minutes is an assumption, labeled as such. |
