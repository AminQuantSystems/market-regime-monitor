# Project charter

**Product:** Market Regime Monitor
**Intended public repository name:** `market-regime-monitor`
**Status:** Product charter. The repository contains the application library. Current phase and instrument status are in `PROJECT_STATE.md`. This charter is not a changelog.

## Product definition

Market Regime Monitor is a deterministic market-state analytics application. The regime is the transparent four-dimensional state — Direction, Momentum, Volatility, and Relative Performance — not one hidden composite score. One of its four instruments is Benchmark Relative Performance against ACWI.

A user should be able to understand the core state of a market in approximately two seconds, without interpreting a conventional multi-line technical-analysis chart.

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

V1 reads a local validated price panel: the bundled synthetic demonstration or a user-supplied CSV. It does not depend on a live market-data API. No production market-data vendor is selected. The approved V1 universe is the US-listed proxy set in `FINANCE_SPEC.md`: SPY, QQQ, IWM, EWU, EWG, EWJ and EEM, with ACWI as the common comparison benchmark for Benchmark Relative Performance. ACWI is not claimed to be the mandate-specific performance benchmark for every regional market. The product does not claim GIPS compliance, CFA approval, or MSCI methodology replication. Direct global-index feeds and FX are later extensions, not V1.

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

The internal Trend states are Strong Up, Up, Neutral, Down, and Strong Down. The public interface presents them as Strong Uptrend, Uptrend, Neutral, Downtrend, and Strong Downtrend. They are not a composite of the other instruments, and they are not trade instructions.

## Design constraints

- Finance calculations live in a tested library, separate from presentation.
- The V1 numerical rules are the owner-approved rules in `FINANCE_SPEC.md`. They are no longer provisional.
- Missing, stale, or insufficient history stops the affected result with an explicit error. Rows are not silently dropped and NaNs are not silently filled.
- Calculations use only information available on or before the observation date. No look-ahead.
- Volatility describes magnitude. It does not make Trend more bullish or more bearish.
- MEEM products share one visual system, specified in `MEEM_DESIGN_SYSTEM.md`. Brand colour identifies MEEM. Semantic colour identifies a financial or system meaning. The same meaning uses the same semantic colour in every MEEM tool.

## Original Phase 0 boundary

The list below is the boundary from when this charter was written. It is not the current repository status.

- Application code
- Package installation
- Market-data download
- Vendor selection
- GitHub repository creation or any publication
- Mac or other remote execution
- Changes to any other project, including Portfolio Risk X-Ray

## Success for Phase 0

The owner has reviewed this charter, the finance specification, the interface concept, and the Windows/Mac integration plan, and has decided which provisional rules become V1 rules.
