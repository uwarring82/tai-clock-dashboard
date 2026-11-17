# Contributor handoff

## First pull request

Build a synthetic-data vertical slice of the historical dashboard. Use an immutable source manifest, a versioned parser, SQLite, and a read-only view. Include a roster and one clock-detail timeline showing phase, declared clock steps, gaps, and the published weight for each computation period.

Use fixtures that exercise clock moves between laboratories, revised releases, positive and zero weights, missing observations, exclusions, and unknown weights. Keep observation status separate from weight status. Store the BIPM clock identifier separately from the reporting laboratory, and track both measurement epoch and release availability.

Preserve the reported sign and reference. The clock files report `UTC(k) − clock`. For `x = pivot − clock`, the clock's fractional frequency relative to the pivot is `−Δx/Δt` when both are in seconds. Keep the sign of published rates and the reference for each imported product.

## Continue from the synthetic pilot

Use the run instructions in the [README](README.md) to verify a fresh build. The fixture adapter in `tai_dashboard/ingest.py` treats each release as a full monthly snapshot. An archive adapter should preserve each BIPM product's individual provenance and availability, since phase, steps and weights may be released independently. The current schemas and JSON endpoints are pilot interfaces.

The synthetic coverage audit is available at `/coverage` and `/api/coverage`. It uses the positively weighted monthly roster as the fixed denominator for every epoch and exposes each incomplete clock-month. The revised October fixture deliberately produces equal count coverage with different weight coverage.

The next worker can catalogue public release metadata and document the source contract for each October product, including its reference, sign, and release availability. Exercise product-specific release cutoffs with synthetic files. Once real data use and retention are cleared, verify source layouts, coverage, and the phase and link signs against the permitted records.

## October 2026 pilot

The public listings identify the October clock files, the `step2610` file, the `w26.10` weights and the `2610/` link period. The record-level audit awaits documented reuse clearance. BIPM asks users to obtain the contributing laboratories' permission for other uses of their submitted data. Confirm the scope for internal audit and retention, and check permission separately for public display or release of derived data. Keep submitted clock records out of this public repository pending clearance. [BIPM reuse notice](https://www.bipm.org/en/time-ftp)

Once cleared, join positive-weight clocks to observations by epoch and report coverage both by count and as a fraction of official weight. Inspect incomplete clock-months before drawing any conclusions about ALGOS eligibility.

- [October clock files and steps](https://webtai.bipm.org/ftp/pub/tai/data/2026/clocks/)
- [Monthly weights](https://webtai.bipm.org/ftp/pub/tai/other-products/weights/)
- [Monthly link comparison archive](https://webtai.bipm.org/ftp/pub/tai/timelinks/lkc/)

## Research milestone

Leave weight replay for a separate research phase. Before implementing it, validate power on the available masks and link covariance. The primary comparison is the 30-day Allan variance of the drift-adjusted difference between candidate free scales, divided by the expected link-only variance. An initial synthetic estimate (not published in this repository; to be reproduced with its script, seed and assumptions before use) suggested 52–70% power over three years to distinguish a twofold variance ratio. An observed excess shows the candidates differ. Establishing which performs better requires an external check. Use official EAL as the shared-input comparison reference.
