# Finance specification — approved V1 model

**Status:** owner-approved V1 finance rules. Phase 0.5.
**Implementation is not authorised.** This document does not add code, data, or a market-data vendor.

These rules replace the provisional Phase 0 proposal. Comparisons are exact. The financial definition uses no tolerance and no epsilon.

## V1 universe

V1 uses US-listed global-equity market proxies so that every series shares one trading calendar. Direct global-index feeds and FX are outside V1.

| market_id | display_name | benchmark_id | enabled | Market State Board card |
|---|---|---|---|---|
| SPY | S&P 500 | ACWI | yes | yes |
| QQQ | Nasdaq 100 | ACWI | yes | yes |
| IWM | Russell 2000 | ACWI | yes | yes |
| EWU | UK equities | ACWI | yes | yes |
| EWG | Germany equities | ACWI | yes | yes |
| EWJ | Japan equities | ACWI | yes | yes |
| EEM | Emerging Markets | ACWI | yes | yes |
| ACWI | global-equity benchmark | none | no | no |

ACWI is required for every relative-strength calculation. It is not a normal board card. Every enabled market uses ACWI as `benchmark_id`.

No production data vendor is selected. V1 input is local validated history.

## Price and observation convention

The canonical price field is `adjusted_close`. Every calculation uses that series.

```text
R(n) = price_t / price_(t-n) - 1
```

`t-n` means n valid trading observations before `t` on that series, not n calendar days.

V1 assumes the enabled proxies and ACWI share the same exchange-date index. The date index of every required series must be identical. Required series are the enabled markets plus ACWI.

No forward-fill, backward-fill, or silent row removal is permitted.

A date is complete when every required series has exactly one finite `adjusted_close` greater than 0 on that date. The latest analysis observation is the latest complete date in the validated panel. If that date is later than `evaluation_date`, validation fails with `DATA_FUTURE_DATE`. Future rows are not dropped to recover an earlier date.

The immediately previous complete observation is the complete date immediately before the latest analysis observation.

## Inputs

`prices.csv`, long form, not created in this phase:

| field | meaning |
|---|---|
| date | exchange date |
| market_id | series identifier |
| adjusted_close | canonical price |

Market configuration, separate from prices, at minimum:

| field | meaning |
|---|---|
| market_id | series identifier |
| display_name | board name |
| benchmark_id | relative-strength benchmark; ACWI for every enabled V1 market |
| enabled | whether the market is a board card and a required series |

ACWI remains required as the benchmark even though `enabled` is no.

## T — Trend

Moving averages are simple moving averages of `adjusted_close`:

- SMA50: arithmetic mean of the latest 50 valid observations, including the observation date
- SMA200: arithmetic mean of the latest 200 valid observations, including the observation date

| Score | Rule | Reason code |
|---:|---|---|
| +2 | price > SMA50 > SMA200 | `TREND_STRONG_UP_ALIGNMENT` |
| +1 | price > SMA200, and the +2 rule is not satisfied | `TREND_UP_ABOVE_200` |
| 0 | price == SMA200 | `TREND_NEUTRAL_AT_200` |
| -1 | price < SMA200, and the -2 rule is not satisfied | `TREND_DOWN_BELOW_200` |
| -2 | price < SMA50 < SMA200 | `TREND_STRONG_DOWN_ALIGNMENT` |

All comparisons are strict except the exact equality that defines score 0. There is no epsilon.

The five rules are exhaustive and disjoint:

- price > SMA200 is either score +2 or score +1
- price == SMA200 is score 0, and it cannot also satisfy +2 or -2
- price < SMA200 is either score -2 or score -1

Equality of price and SMA50, or of SMA50 and SMA200, fails the strict chain and falls through to +1 or -1 as the table requires. Those equalities need explicit tests. They do not get a tolerance band.

## M — Momentum

Simple returns:

```text
R21 = price_t / price_(t-21) - 1
R63 = price_t / price_(t-63) - 1
```

Geometric daily pace, used only when both returns are strictly positive or both are strictly negative:

```text
G(n) = (price_t / price_(t-n))^(1/n) - 1
```

| State | Rule | Reason code |
|---|---|---|
| Accelerating | R21 > 0 and R63 > 0 and G21 > G63 | `MOMENTUM_ACCELERATING` |
| Positive | R21 > 0 and R63 > 0 and G21 <= G63 | `MOMENTUM_POSITIVE` |
| Mixed | either return equals 0, or R21 and R63 have opposite signs | `MOMENTUM_MIXED` |
| Negative | R21 < 0 and R63 < 0 and G21 >= G63 | `MOMENTUM_NEGATIVE` |
| Deteriorating | R21 < 0 and R63 < 0 and G21 < G63 | `MOMENTUM_DETERIORATING` |

Equal pace is not mixed. G21 == G63 with both returns positive is Positive. G21 == G63 with both returns negative is Negative.

The sign pairs cover every combination:

- any zero return, including both zero: Mixed
- opposite nonzero signs: Mixed
- both positive: Accelerating or Positive, split by G21 > G63 versus G21 <= G63
- both negative: Deteriorating or Negative, split by G21 < G63 versus G21 >= G63

No pair of states matches the same returns.

Momentum direction, used only by the directional table:

| Momentum direction | States |
|---|---|
| positive | Accelerating, Positive |
| neutral | Mixed |
| negative | Negative, Deteriorating |

## V — Volatility

Daily return:

```text
ln(price_t / price_(t-1))
```

Current realised volatility uses the latest 20 daily log returns:

- sample standard deviation with divisor `n - 1` (`ddof=1`)
- annualised by multiplying by `sqrt(252)`

The reference distribution is the previous 252 rolling 20-day realised-volatility observations. The current observation is not a member of that distribution.

Empirical percentile:

```text
percentile = 100 * count(previous_volatility <= current_volatility) / 252
```

| Regime | Rule | Reason code |
|---|---|---|
| Low | percentile <= 25 | `VOLATILITY_LOW` |
| Normal | 25 < percentile <= 75 | `VOLATILITY_NORMAL` |
| Elevated | 75 < percentile <= 90 | `VOLATILITY_ELEVATED` |
| High | percentile > 90 | `VOLATILITY_HIGH` |

The four bands partition every real percentile. Exact boundaries:

- percentile 25 is Low
- percentile 75 is Normal
- percentile 90 would be Elevated

With a denominator of 252, attainable percentiles are `100 * k / 252` for an integer count `k` from 0 through 252. This hits 25 exactly at `k = 63` and 75 exactly at `k = 189`. It never hits 90, because `90 * 252 / 100 = 226.8` is not an integer. The boundary test is therefore the adjacent attainable values:

- `k = 226` gives `22600 / 252 = 89.6825...`, which is Elevated
- `k = 227` gives `22700 / 252 = 90.0793...`, which is High

Volatility does not enter the directional state. A high or low regime is not bullish or bearish.

## R — Relative strength

```text
relative_strength = asset_R63 - ACWI_R63
```

Both returns use the approved simple 63-observation return. The result is a decimal return. A difference of 0.02 is two percentage points.

| State | Rule | Reason code |
|---|---|---|
| Leader | relative_strength >= 0.05 | `RELATIVE_STRENGTH_LEADER` |
| Strong | 0.02 <= relative_strength < 0.05 | `RELATIVE_STRENGTH_STRONG` |
| Neutral | -0.02 < relative_strength < 0.02 | `RELATIVE_STRENGTH_NEUTRAL` |
| Weak | -0.05 < relative_strength <= -0.02 | `RELATIVE_STRENGTH_WEAK` |
| Laggard | relative_strength <= -0.05 | `RELATIVE_STRENGTH_LAGGARD` |

These five intervals partition the real line and do not overlap. Exact boundaries:

- +0.05 is Leader
- +0.02 is Strong
- -0.02 is Weak
- -0.05 is Laggard

Neutral is the open interval between -0.02 and +0.02.

Relative-strength direction, used only by the directional table:

| Relative-strength direction | States |
|---|---|
| positive | Leader, Strong |
| neutral | Neutral |
| negative | Weak, Laggard |

Leaders and laggards on the board are ordered by this continuous value, not by the category alone. ACWI is not ranked as a board card.

## Directional state

Direction uses Trend, Momentum direction, and Relative-strength direction only. Volatility is excluded.

This is a decision table with a fixed precedence. It is not a sum, a weighted score, or a hidden composite.

| Order | State | Rule | Reason code |
|---:|---|---|---|
| 1 | Strong Up | Trend == +2 and momentum direction is positive and relative-strength direction is positive | `STATE_STRONG_UP` |
| 2 | Strong Down | Trend == -2 and momentum direction is negative and relative-strength direction is negative | `STATE_STRONG_DOWN` |
| 3 | Up | Trend > 0 and at least one of momentum direction or relative-strength direction is positive | `STATE_UP` |
| 4 | Down | Trend < 0 and at least one of momentum direction or relative-strength direction is negative | `STATE_DOWN` |
| 5 | Neutral | every remaining combination | `STATE_NEUTRAL` |

The first matching row wins. Rows 3 and 4 are reached only when rows 1 and 2 have not matched, which is the required exclusion of Strong Up from Up and of Strong Down from Down.

Coverage of the 45 combinations (5 trend scores × 3 momentum directions × 3 relative-strength directions):

| State | Combinations | Why there is no second match |
|---|---:|---|
| Strong Up | 1 | Trend is +2, so Strong Down, Down, and Neutral do not apply. The Up row is not reached. |
| Strong Down | 1 | Trend is -2, so Strong Up, Up, and Neutral do not apply. The Down row is not reached. |
| Up | 9 | Trend is +1 or +2, so Down and Strong Down do not apply. The one Strong Up combination was already taken. |
| Down | 9 | Trend is -1 or -2, so Up and Strong Up do not apply. The one Strong Down combination was already taken. |
| Neutral | 25 | Complement: 45 − 1 − 1 − 9 − 9. Includes Trend 0 with any confirmation, and a positive trend opposed by both non-positive momentum and relative strength. |

A positive trend with negative momentum and negative relative strength is Neutral. It is not Up, because neither confirmation is positive, and it is not Strong Up. The mirror image, a negative trend with both confirmations positive, is Neutral.

These labels are state names. They are not buy or sell signals and they are not forecasts.

## What changed

Compare the latest complete observation with the immediately previous complete observation.

### Current-state minimum history

- 273 valid price observations are sufficient to calculate the latest complete market state.
- 272 observations fail with `DATA_INSUFFICIENT_HISTORY`. No current state is published.

### What Changed minimum history

- 274 valid price observations are required to calculate both the latest complete state and the immediately previous complete state.
- At exactly 273 observations, the current state succeeds and the previous-session comparison is unavailable.

At exactly 273 observations the engine must not return:

```text
No market-state change since previous session
```

No valid comparison has been made. The result is:

```text
change_status = unavailable
```

with reason code `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`.

The sentence `No market-state change since previous session` is produced only when all three of these are true:

- at least 274 valid observations exist
- both the latest state and the previous state were calculated successfully
- none of the five categorical states changed

Those five states are the directional state, Trend, Momentum, Volatility, and Relative Strength. A difference in any of them is a categorical transition. Each transition names the instrument, the previous label, the new label, and the reason code.

This comparison is specified here and is not implemented in Phase 1A. Phase 1A only enforces the 273-observation input minimum.

## Freshness and reproducibility

`evaluation_date` is an explicit engine input. Staleness does not read a system clock.

Let the latest complete observation be date `D`.

```text
age = evaluation_date - D, in calendar days
```

| Relationship | Result |
|---|---|
| `D` later than `evaluation_date` | `DATA_FUTURE_DATE` |
| age 0 through 5 | eligible |
| age 6 or more | `DATA_STALE` |

Exactly 5 calendar days is accepted. Exactly 6 is rejected. A later observation is not trimmed back to an earlier date.

Reproducibility contract:

```text
same price data + same configuration + same evaluation_date = same output
```

## Minimum history

A full current state requires 273 valid price observations on the shared date index for every required series.

The number is fixed by the volatility window: 21 prices for the first 20-day volatility, plus 252 previous volatility observations, with the current observation excluded. The first price used by that construction is 272 observations before the analysis date, so the series length is 273. Trend and momentum need less history than that.

272 valid observations fail with `DATA_INSUFFICIENT_HISTORY`. No partial state is published.

## Validation

Failures are explicit. No affected output is published with a substituted value.

| Condition | Reason code |
|---|---|
| Latest complete observation is later than `evaluation_date` | `DATA_FUTURE_DATE` |
| Latest complete observation is more than 5 calendar days before `evaluation_date` | `DATA_STALE` |
| A required series is absent, or is absent from a date that the shared index requires | `DATA_MISSING_MARKET` |
| More than one row exists for the same `market_id` and `date` | `DATA_DUPLICATE_DATE` |
| Fewer than 273 valid observations through the analysis date | `DATA_INSUFFICIENT_HISTORY` |
| `adjusted_close` is non-numeric, non-finite, or not greater than 0 | `DATA_INVALID_PRICE` |
| `adjusted_close` is blank or missing | `DATA_MISSING_VALUE` |

Duplicate keys fail even when the two prices are equal.

## Reason codes

Finance classifications:

- `TREND_STRONG_UP_ALIGNMENT`
- `TREND_UP_ABOVE_200`
- `TREND_NEUTRAL_AT_200`
- `TREND_DOWN_BELOW_200`
- `TREND_STRONG_DOWN_ALIGNMENT`
- `MOMENTUM_ACCELERATING`
- `MOMENTUM_POSITIVE`
- `MOMENTUM_MIXED`
- `MOMENTUM_NEGATIVE`
- `MOMENTUM_DETERIORATING`
- `VOLATILITY_LOW`
- `VOLATILITY_NORMAL`
- `VOLATILITY_ELEVATED`
- `VOLATILITY_HIGH`
- `RELATIVE_STRENGTH_LEADER`
- `RELATIVE_STRENGTH_STRONG`
- `RELATIVE_STRENGTH_NEUTRAL`
- `RELATIVE_STRENGTH_WEAK`
- `RELATIVE_STRENGTH_LAGGARD`
- `STATE_STRONG_UP`
- `STATE_UP`
- `STATE_NEUTRAL`
- `STATE_DOWN`
- `STATE_STRONG_DOWN`

Validation codes:

- `DATA_STALE`
- `DATA_FUTURE_DATE`
- `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`
- `DATA_MISSING_MARKET`
- `DATA_DUPLICATE_DATE`
- `DATA_INSUFFICIENT_HISTORY`
- `DATA_INVALID_PRICE`
- `DATA_MISSING_VALUE`

## Determinism requirements

- The same prices, configuration, and `evaluation_date` produce the same labels, reason codes, measurements, and ordering.
- Every published label has the measurements and the reason code that selected it.
- Calculations on date `t` use observations on or before `t` only.
- The interface, when it is later built, formats these outputs and does not calculate them.
- Exact boundary cases are specified in `GOLDEN_CASES.md`.

## Not in V1

- A production market-data vendor
- Live API dependence
- Direct global-index feeds
- FX conversion
- Buy or sell signals, price forecasts, or turning-point claims
- Any use of volatility inside the directional table
