# Project charter

**Product:** Market Regime Monitor
**Intended public repository name:** `market-regime-monitor`
**Status:** Phase 0 — product and finance design. No application code.

## Product definition

Market Regime Monitor is a deterministic market-regime scanner. One of its four instruments is Benchmark Relative Performance against ACWI.

A user should be able to understand the state of a group of financial markets within approximately 3–5 seconds, without interpreting a conventional multi-line technical-analysis chart.

## Core objective

Communicate, for each configured market and for the group:

- whether the prevailing trend is aligned up, aligned down, or not fully aligned
- whether shorter-horizon and medium-horizon momentum agree, conflict, or are deteriorating
- whether realised volatility is low, normal, elevated, or high relative to that asset's own history
- whether the asset is outperforming or underperforming the common ACWI comparison benchmark over 63 trading observations
- what changed since the previous observation

Every displayed state must be explainable from named inputs, named rules, and a reason code. The same validated input must always produce the same output.

## V1 scope

V1 focuses only on:

- trend
- momentum
- realised volatility
- benchmark relative performance
- state transitions ("What changed?")
- deterministic explainability

V1 reads local, validated historical price data. It does not depend on a live market-data API. No production market-data vendor is selected. The approved V1 universe is the US-listed proxy set in `FINANCE_SPEC.md`: SPY, QQQ, IWM, EWU, EWG, EWJ and EEM, with ACWI as the common comparison benchmark for Benchmark Relative Performance. ACWI is not claimed to be the mandate-specific performance benchmark for every regional market. The product does not claim GIPS compliance, CFA approval, or MSCI methodology replication. Direct global-index feeds and FX are later extensions, not V1.

The interface displays results. It does not calculate them.

## Anti-goals

V1 will not:

- emit BUY or SELL signals
- predict prices
- produce AI-generated market opinions
- publish a black-box confidence score
- publish an unexplained composite metric
- present a chart crowded with technical-indicator lines
- claim that the system predicts turning points

Directional labels such as Strong Up and Strong Down describe the current rule-based state. They are not trade instructions.

## Design constraints

- Finance calculations live in a tested library, separate from presentation.
- The V1 numerical rules are the owner-approved rules in `FINANCE_SPEC.md`. They are no longer provisional.
- Missing, stale, or insufficient history stops the affected result with an explicit error. Rows are not silently dropped and NaNs are not silently filled.
- Calculations use only information available on or before the observation date. No look-ahead.
- Volatility describes magnitude. It does not make a directional state more bullish or more bearish.

## Out of scope for this phase

- Application code
- Package installation
- Market-data download
- Vendor selection
- GitHub repository creation or any publication
- Mac or other remote execution
- Changes to any other project, including Portfolio Risk X-Ray

## Success for Phase 0

The owner has reviewed this charter, the finance specification, the interface concept, and the Windows/Mac integration plan, and has decided which provisional rules become V1 rules.
