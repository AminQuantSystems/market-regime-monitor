# Project state

**Project:** Market Regime Monitor
**Intended repository name, not created:** `market-regime-monitor`
**Package version:** 1.0.0 in `pyproject.toml`. Future public tag, not created: `v1.0.0`.
**As of:** 21 October 2026

## Phase

Market Regime Monitor V1.0.0 is ready for owner-authorised publication.

Functionality is complete and frozen. The finance core, API, and frontend are hardened. Public terminology is approved. Human-facing prose uses British English. The source-code licence is Apache License 2.0. MEEM Technologies branding is proprietary and excluded from that licence. The historical machine-local working-copy path has been removed from Git history. The README and screenshots are public-ready. Continuous integration is configured and has not been run on GitHub. There is no GitHub remote. Publication has not been performed. The future release tag is `v1.0.0`, and it has not been created.

## What exists

- Owner-approved finance rules in `FINANCE_SPEC.md`
- Acceptance cases in `GOLDEN_CASES.md`
- A local Python package, `market_state`, with configuration and price validation. The import name is unchanged.
- The Trend instrument in `src/market_state/trend.py`
- The Momentum instrument in `src/market_state/momentum.py`
- The realised-volatility instrument in `src/market_state/volatility.py`
- The Benchmark Relative Performance instrument in `src/market_state/relative_performance.py`
- The Market Regime Snapshot orchestrator in `src/market_state/regime.py`
- The What Changed comparison in `src/market_state/change.py`
- Pytest coverage for validation, Trend, Momentum, Volatility, Benchmark Relative Performance, snapshot orchestration, and categorical change
- The MEEM Toolkit Design System v1.0 in `MEEM_DESIGN_SYSTEM.md` and `MEEM_DESIGN_TOKENS.json`
- The Market State Board and detail specification in `UI_CONCEPT.md`
- The UI technology and API architecture in `UI_ARCHITECTURE.md`
- A thin FastAPI adapter in `app/api/`
- A synthetic demonstration panel in `app/demo/`
- A React, TypeScript, and Vite board in `frontend/`
- This file, plus the read-only Windows/Mac plan

## History rule

The validator accepts 274 observations and rejects 273 and 272 with `DATA_INSUFFICIENT_HISTORY`.

274 observations are the full current-state minimum. The earliest reference RV21, at `t-252`, needs the price at `t-273`. The complete What Changed minimum is 275. At 274 the current snapshot can exist and the previous complete snapshot cannot, so the designed status is `UNAVAILABLE` with `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`. `No market-state change since previous session` is drill-down text only for `UNCHANGED`, when at least 275 observations exist, both snapshots were calculated, and none of the four categorical labels changed: Direction, Momentum, Volatility, and Benchmark Relative Performance.

An observation later than `evaluation_date` is `DATA_FUTURE_DATE`. What Changed is implemented. The local project folder has not been renamed.

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
- Market Regime Snapshot: implemented and integrity-hardened. It assembles `TrendResult`, `MomentumResult`, `VolatilityResult`, and `RelativePerformanceResult` for one selected market and one as-of date. It does not call full-board validation. A component identity that contradicts the request fails with `MarketRegimeError` and `REGIME_COMPONENT_MISMATCH`. Direction is `trend.trend_state`. No composite directional regime exists. This assembly is not independent bank model validation or regulatory approval.
- What Changed: implemented. It compares the four categorical labels on the current snapshot and the immediately previous observation. Statuses are `CHANGED`, `UNCHANGED`, and `UNAVAILABLE`. It calculates no finance.
- Finance and monitoring core: frozen
- Tests: 327 Python tests passed. The original 309 finance and monitoring tests remain passing. Four nested-identity checks were added to the pure comparator. Fourteen adapter tests cover the weekday demonstration contract, same-bytes demo/upload finance equivalence, categorical response literals, the request-validation envelope, and the OpenAPI enums. Frontend tests: 28 passed, including the public Direction presentation labels.
- MEEM production brand palette: locked
- MEEM Toolkit Design System: v1.0 specified
- Original finance tests: 309 passed, plus 4 nested-identity checks
- FastAPI adapter: implemented
- Synthetic demo: weekday-only, implemented. 275 Monday–Friday observations from 2025-02-17 through 2026-03-06. No exchange calendar.
- Official MEEM mark: implemented. The asset is unchanged. The header renders it at 24 px wide, about 43 px tall.
- CSV upload API boundary: implemented
- CSV upload user experience: implemented
- Return to Demo: implemented
- Frontend: React, TypeScript, and Vite implemented
- MEEM design-token adapter: implemented
- Application shell: implemented
- Market State Board: implemented
- Market row selection: implemented
- Market Detail Panel: implemented. Trend Score is not rendered. `trend_score` remains in the finance result and the API.
- What Changed detail: implemented
- Charts: not implemented
- Live or vendor market data: not implemented
- Backtesting: not implemented
- Database: none
- Authentication: none
- Mac integration: not authorised
- GitHub publication: none
- Current snapshot minimum: 274
- Complete What Changed minimum: 275

## Data and operations

- No live or vendor market data exists. Tests use synthetic local frames only.
- No production data vendor is selected.
- Mac integration remains unauthorised.
- Nothing has been published. There is no GitHub remote.
- Portfolio Risk X-Ray was not modified.

## Local orchestration timing

One local measurement on 21 October 2026, Python 3.14, this Windows machine: assembling snapshots for SPY, QQQ, IWM, EWU, EWG, EWJ, and EEM from one synthetic 274-observation panel took 0.22 seconds. The same seven markets, each with What Changed, on one synthetic 275-observation panel took 0.32 seconds. The panel also contained ACWI. Both figures are diagnostic evidence only. They are not pass/fail limits. This workload provides no evidence that Mac offload is justified. No concurrency and no multiprocessing have been added. A later Mac measurement may matter for a large historical backtest, a parameter sweep, a scenario grid, or another large multi-period research workload. It is not relevant to the current seven-market snapshot or What Changed comparison.

## Release-candidate notes

- The pure comparator now rejects a manually constructed snapshot whose nested component market or date disagrees with the snapshot, and a relative-performance benchmark that is blank or disagrees with the other snapshot. The code remains `CHANGE_SNAPSHOT_MISMATCH`. Production formulas are unchanged.
- Categorical API fields use closed literals. Reason codes stay strings. Omitted required form fields return HTTP 422 with `API_REQUEST_VALIDATION` and category `request`. Explicit adapter errors are unchanged.
- What Changed stays the fifth detail section. Removing the Trend Score row is the only vertical change. Section spacing was left at 12 px because tighter gaps would make the evidence harder to read. At 1600 × 1400 the whole detail fits. At 1366 × 768, with the upload form open, What Changed begins below the fold. That short scroll is accepted V1 behaviour.
- Source code is licensed under the Apache License 2.0. MEEM Technologies branding is proprietary and is not included in that licence. See `LICENSE` and `BRANDING.md`.
- Direction on screen uses Strong Uptrend, Uptrend, Neutral, Downtrend, and Strong Downtrend. The API Trend states remain Strong Up, Up, Neutral, Down, and Strong Down.
- No GitHub remote, release, or tag has been created.

## Next approved action

Stop after the local V1.0.0 publication-preparation report. Do not create a remote, push, publish, or tag until the owner authorises publication.
