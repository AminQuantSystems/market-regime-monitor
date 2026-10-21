# Project state

**Project:** Market Regime Monitor
**Local root:** `<local-worktree>`
**Intended repository name, not created:** `market-regime-monitor`
**As of:** 21 October 2026

## Phase

Phase 1G — Market Regime Snapshot orchestration implemented.

## What exists

- Owner-approved finance rules in `FINANCE_SPEC.md`
- Acceptance cases in `GOLDEN_CASES.md`
- A local Python package, `market_state`, with configuration and price validation. The import name is unchanged.
- The Trend instrument in `src/market_state/trend.py`
- The Momentum instrument in `src/market_state/momentum.py`
- The realised-volatility instrument in `src/market_state/volatility.py`
- The Benchmark Relative Performance instrument in `src/market_state/relative_performance.py`
- The Market Regime Snapshot orchestrator in `src/market_state/regime.py`
- Pytest coverage for validation, Trend, Momentum, Volatility, Benchmark Relative Performance, and snapshot orchestration
- This file, plus the interface concept and the read-only Windows/Mac plan

## History rule

The validator accepts 274 observations and rejects 273 and 272 with `DATA_INSUFFICIENT_HISTORY`.

274 observations are the full current-state minimum. The earliest reference RV21, at `t-252`, needs the price at `t-273`. The planned complete What Changed minimum is 275. At 274 the current full state can be available and the previous full state cannot, so `change_status = unavailable` with `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`. `No market-state change since previous session` is allowed only when at least 275 observations exist, both states were calculated, and none of the four dimensions changed: Direction / Trend, Momentum, Volatility, and Benchmark Relative Performance.

An observation later than `evaluation_date` is `DATA_FUTURE_DATE`. What Changed itself is not implemented. The local project folder has not been renamed.

## Validation contract

- Every configured market uses `benchmark_id = ACWI`, including disabled extra markets.
- ACWI is mandatory, `enabled = False`, and `benchmark_id = ACWI`. That self-reference is schema uniformity only.
- `enabled` is accepted only as a semantic boolean: Python bool, NumPy boolean scalar, or non-null pandas nullable boolean. An object column of Python booleans is valid. Strings and numbers are rejected.
- Blank or whitespace-padded configuration text is rejected and is not trimmed.
- `DATA_MISSING_MARKET` means a required instrument has no rows. `DATA_DATE_INDEX_MISMATCH` means the instrument is present on a different date set.
- Validation is deterministic and first-failure-wins. Configuration is checked before prices. Schema and values are checked before history and freshness.

## Instrument status

- Validation: implemented
- Trend: implemented
- Momentum: implemented
- Volatility: implemented. RV21 uses 21 zero-mean log returns and annualises with 252. The regime percentile is `100 * (L + 0.5 * E) / 252`, a Market Regime Monitor half-weight tie convention. A history in which every RV21 equals today's value is percentile 50 and Normal.
- Benchmark Relative Performance: implemented and numerically hardened. The measure is the 63-observation active return against ACWI, the common V1 comparison benchmark. Classification treats a value within `1e-12` of +0.05, +0.02, -0.02, or -0.05 as that threshold. The stored active return stays at full precision. ACWI is not the mandate-specific benchmark for every regional market.
- Market Regime Snapshot: implemented. It assembles `TrendResult`, `MomentumResult`, `VolatilityResult`, and `RelativePerformanceResult` for one market and one as-of date. It adds no finance methodology. Direction is `trend.trend_state`. No composite directional regime exists. This assembly is not independent bank model validation or regulatory approval.
- What Changed: not implemented
- UI: not implemented
- Live or vendor market data: not implemented
- Backtesting: not implemented
- Mac integration: not authorised
- GitHub publication: none
- Full current-state and snapshot minimum: 274
- Planned complete What Changed minimum: 275

## Data and operations

- No live or vendor market data exists. Tests use synthetic local frames only.
- No production data vendor is selected.
- Mac integration remains unauthorised.
- Nothing has been published. There is no GitHub remote.
- Portfolio Risk X-Ray was not modified.

## Local orchestration timing

One local measurement on 21 October 2026, Python 3.14, this Windows machine: assembling snapshots for SPY, QQQ, IWM, EWU, EWG, EWJ, and EEM from one synthetic 274-observation panel took 0.22 seconds. The panel also contained ACWI. This is diagnostic evidence only. It is not a pass/fail limit, and it does not authorise a Mac worker or parallel execution.

## Next approved action

Stop after Phase 1G. Do not implement What Changed or UI until that work is authorised.
