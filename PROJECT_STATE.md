# Project state

**Project:** Market State Flight Deck
**Local root:** `<local-worktree>`
**Intended repository name, not created:** `market-state-flight-deck`
**As of:** 21 October 2026

## Phase

Phase 1A — Project skeleton and deterministic data validation implemented.

## What exists

- Owner-approved finance rules in `FINANCE_SPEC.md`
- Acceptance cases in `GOLDEN_CASES.md`
- A local Python package, `market_state`, with configuration and price validation
- Pytest coverage for that validation contract
- This file, plus the interface concept and the read-only Windows/Mac plan

## History rule

- 273 valid observations are sufficient for the latest complete market state.
- 272 observations fail with `DATA_INSUFFICIENT_HISTORY`.
- 274 valid observations are required before What Changed can calculate both the latest state and the previous state.
- At exactly 273 observations the current state succeeds, `change_status = unavailable`, and the reason code is `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`.
- `No market-state change since previous session` is allowed only when at least 274 observations exist, both states were calculated, and none of the five categorical states changed.
- An observation later than `evaluation_date` is `DATA_FUTURE_DATE`.

What Changed itself is not implemented. Phase 1A only enforces the 273-observation input minimum and the freshness rules.

## Explicitly not implemented

- Trend
- Momentum
- Volatility
- Relative Strength
- Directional state
- What Changed
- UI

## Data and operations

- No live or vendor market data exists. Tests use synthetic local frames only.
- No production data vendor is selected.
- Mac integration remains unauthorised.
- Nothing has been published. There is no GitHub remote.
- Portfolio Risk X-Ray was not modified.

## Next approved action

Stop at Phase 1A. Do not start indicator calculations until the owner approves Phase 1B.
