# Finance specification — approved V1 model

**Status:** owner-approved V1 finance rules.
Phase 1A implements deterministic validation of prices and configuration. Phase 1B implements Trend. Phase 1C implements Momentum. Phase 1D implements realised volatility. Relative strength, directional state, and What Changed are specified here and are not implemented.

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
| ACWI | global-equity benchmark | ACWI | no | no |

ACWI is mandatory. It is the V1 benchmark and is required for every relative-strength calculation. It is not a normal board card, and its relative strength is not calculated or displayed as a board-market result.

ACWI's `benchmark_id` is `ACWI` only so the configuration schema stays uniform. ACWI's `enabled` value is `False`.

Every configured market uses `benchmark_id = ACWI`. That includes every enabled market, ACWI itself, and any disabled extra market. A disabled extra market may appear in the configuration, and it may be absent from the shared date-index check, but it still uses ACWI. V1 does not give disabled markets a different benchmark.

No production data vendor is selected. V1 input is local validated history.

## Price and observation convention

The canonical price field is `adjusted_close`. Every calculation uses that series.

```text
R(n) = price_t / price_(t-n) - 1
```

`t-n` means n valid trading observations before `t` on that series, not n calendar days.

V1 assumes the enabled proxies and ACWI share the same exchange-date index. The date index of every required series must be identical. Required series are the enabled markets plus ACWI.

`DATA_MISSING_MARKET` means a required instrument has no rows at all. `DATA_DATE_INDEX_MISMATCH` means the instrument is present, but its set of dates differs from the required shared date index. That includes a missing first date, a missing internal date, a missing latest date, an extra date, and the case where every required series has the same row count on different dates.

No forward-fill, backward-fill, interpolation, or silent row removal is permitted.

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
| benchmark_id | `ACWI` for every configured V1 market, including ACWI and disabled extra markets |
| enabled | whether the market is a board card and a required series |

`enabled` is a boolean. Accepted values are Python `True`/`False`, NumPy boolean scalars, and non-null pandas nullable-boolean values. The column dtype alone does not decide validity: an object column of genuine Python booleans is valid. Strings (`True`, `False`, `yes`, `no`), numbers (`1`, `0`, `1.0`, `0.0`), null, and `pd.NA` are rejected.

`market_id`, `display_name`, and `benchmark_id` are exact text. Empty text and whitespace-only text are missing. Surrounding whitespace is invalid. Validation does not trim or rewrite those fields.

ACWI remains a required price series even though `enabled` is `False`.

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

V1 Momentum is short/medium-horizon time-series market-state momentum. It asks whether recent adjusted-close movement is positive or negative, and whether the recent per-observation pace is strengthening or weakening relative to the medium-term pace. Trend already represents the slower 50/200 structural direction.

This is not the academic 12-minus-1 equity factor, not a cross-sectional stock-selection factor, and not a 6-month or 12-month institutional momentum signal. Those slower horizons are possible future research. They are not part of V1. The 21- and 63-observation windows are for responsiveness in Market Regime Monitor. They are not a claim of a universal institutional standard.

Momentum is not a buy or sell signal, a position size, a volatility-adjusted allocation, or a price forecast. R21 and R63 are not divided by volatility. Volatility and relative strength stay separate instruments. Later portfolio construction may scale by volatility. V1 Momentum does not.

Lookbacks are trading observations, not calendar days. Prices are `adjusted_close`. There is no fill, interpolation, or use of a later observation.

```text
R21 = price_t / price_(t-21) - 1
R63 = price_t / price_(t-63) - 1
P(n) = ln(price_t / price_(t-n)) / n
P21 = ln(price_t / price_(t-21)) / 21
P63 = ln(price_t / price_(t-63)) / 63
G(n) = exp(P(n)) - 1
```

P21 versus P63 decides whether pace is strengthening or weakening. G(n) is the earlier geometric daily rate. The exponential is strictly increasing, so P21 > P63 is the same ordering as G21 > G63. Pace is not annualised. Comparisons are exact. There is no tolerance and no rounding before classification.

The calculation uses only the requested market on or before the exact as-of date. A missing date is not replaced by a neighbour. Later rows are ignored and are not borrowed to meet the history minimum.

`price_(t-63)` is 63 observations before `t`, so the Momentum unit needs at least 64 observations through the as-of date. 63 observations fail with `DATA_INSUFFICIENT_HISTORY`. The market-data validator requires 274 observations for a full current state. Momentum's own unit minimum remains 64.

`classify_momentum` is a predicate on four pre-calculated numbers. Each return and its pace are expected to come from the same positive price ratio. The predicate does not recompute a ratio and does not reject a finite tuple that could not have come from one ratio. `calculate_momentum` is the normal public path. It builds both pairs from the same positive adjusted closes.

A finite positive pair of prices can still underflow to a zero ratio or overflow to a non-finite ratio. That ratio is `DATA_INVALID_PRICE`. The calculation does not clip, floor, or substitute an epsilon, and it does not leak a raw math exception.

| State | Rule | Reason code |
|---|---|---|
| Accelerating | R21 > 0 and R63 > 0 and P21 > P63 | `MOMENTUM_ACCELERATING` |
| Positive | R21 > 0 and R63 > 0 and P21 <= P63 | `MOMENTUM_POSITIVE` |
| Mixed | either return equals 0, or R21 and R63 have opposite signs | `MOMENTUM_MIXED` |
| Negative | R21 < 0 and R63 < 0 and P21 >= P63 | `MOMENTUM_NEGATIVE` |
| Deteriorating | R21 < 0 and R63 < 0 and P21 < P63 | `MOMENTUM_DETERIORATING` |

Negative means both horizons are negative and the recent pace is equal to, or less negative than, the medium-term pace. Deteriorating means both are negative and the recent pace is more negative than the medium-term pace.

Equal pace is not mixed. P21 == P63 with both returns positive is Positive. P21 == P63 with both returns negative is Negative.

The sign pairs cover every combination:

- any zero return, including both zero: Mixed
- opposite nonzero signs: Mixed
- both positive: Accelerating or Positive, split by P21 > P63 versus P21 <= P63
- both negative: Deteriorating or Negative, split by P21 < P63 versus P21 >= P63

No pair of states matches the same returns. The calculation owns these formulas. Raw panel validity stays with market-data validation.

Momentum direction, used only by the directional table:

| Momentum direction | States |
|---|---|
| positive | Accelerating, Positive |
| neutral | Mixed |
| negative | Negative, Deteriorating |

## V — Volatility

**Status:** implemented in `src/market_state/volatility.py`.

V1 Volatility is a backward-looking realised-movement magnitude instrument. It asks how large recent daily price movements have been relative to this market's own recent history.

It does not say whether the market is bullish or bearish. It is not expected future volatility, implied volatility, value at risk, expected loss, a position size, or a trade direction. Volatility does not enter the directional state. A high or low regime is not bullish or bearish.

The 21-session calculation is deliberately aligned with the transparent realised-volatility construction published in the Cboe Realized Volatility Index methodology. Market Regime Monitor does not reproduce the Cboe index. Cboe RVOL derives its underlying spot value under its own index methodology. Market Regime Monitor uses validated `adjusted_close` market-proxy prices and adds its own historical percentile regime.

The 252-observation percentile and the 25/75/90 labels are a Market Regime Monitor classification choice. They are not a Cboe standard and they are not a universal institutional standard. Their purpose is an interpretable asset-relative state.

### RV21

`N = 21` trading-observation log returns ending at `t`. Lookbacks are observations, not calendar days.

```text
r_i = ln(price_i / price_(i-1))
RV21_t = sqrt( (252 / 21) * sum(r_i^2 for the latest 21 returns) )
        = sqrt( 252 * mean(r_i^2 for the latest 21 returns) )
```

The two forms are the same. The result is a decimal: 0.20 means 20% annualised. Percentage formatting belongs to a later UI.

Construction rules:

- Use 21 returns, so a standalone RV21 needs 22 prices. 21 prices are insufficient.
- Use log returns of `adjusted_close`. Each return is `ln(price_i) - ln(price_(i-1))`, which is the same real number as `ln(price_i / price_(i-1))`. The difference of logs is the implementation, so an extreme finite ratio is not formed first.
- Set the return mean to zero by construction. Sum the squares. Do not subtract the sample mean.
- Do not use a sample standard deviation, `ddof=1`, or 20 returns.
- Annualise with 252.
- Do not clip, floor, or introduce an epsilon.

This is the root-mean-square size of the daily log moves. Subtracting the sample mean would measure dispersion around recent drift and would mix a return estimate into a magnitude instrument. That is not the approved construction. Sign does not enter, because each return is squared. A constant price has every return at 0, so RV21 is 0. Any path whose absolute log returns are the constant `c` has `RV21 = abs(c) * sqrt(252)`, including a path that alternates in sign.

### Regime

The Cboe reference applies only to the RV21 measurement above. The historical percentile is a Market Regime Monitor design. Cboe does not specify this regime, and the 25/75/90 bands are not a Cboe standard or a universal institutional standard.

The percentile answers where today's realised volatility sits relative to this market's previous 252 realised-volatility observations. It is a descriptive historical rank. It is not the probability that volatility will rise or fall, not a confidence level, not a p-value, not a tail probability, not a forecast, and not a claim of statistical significance. Consecutive 21-observation RV21 values overlap and are serially dependent, so the rank is not treated as a sample of independent draws.

Calculate today's RV21. Compare it with the previous 252 RV21 observations for the same market. Today's value is not a member of that reference distribution. The earlier rule `100 * count(previous_rv21 <= current_rv21) / 252` is withdrawn. Under that rule, a value identical to its entire history scored 100 and was classified High. A relative historical-state classifier does not treat an observation identical to every reference value as an extreme upper-tail observation.

```text
L = count(previous_rv21 < current_rv21)
E = count(previous_rv21 == current_rv21)
N = 252
historical_percentile = 100 * (L + 0.5 * E) / N
```

Values strictly below today's RV21 receive full weight. Values exactly equal to it receive half weight. Values strictly above it receive zero weight. A value identical to its entire historical reference set receives percentile 50. This is a deliberate half-weight / mid-distribution tie convention used by Market Regime Monitor. It is conceptually related to handling ties at the middle of their tied block. It is not the conventional average of the ranks `L+1` through `L+E`, which is `L + (E + 1) / 2` and sits half a rank above `L + 0.5 * E`. The implemented equation is not attributed to an external ranking standard. Comparisons are exact. There is no tolerance, no epsilon, no interpolation, and no external statistics routine.

| Regime | Rule | Reason code |
|---|---|---|
| Low | percentile <= 25 | `VOLATILITY_LOW` |
| Normal | 25 < percentile <= 75 | `VOLATILITY_NORMAL` |
| Elevated | 75 < percentile <= 90 | `VOLATILITY_ELEVATED` |
| High | percentile > 90 | `VOLATILITY_HIGH` |

The four bands partition every real number, so every attainable percentile belongs to exactly one regime. Exact 25 is Low. Exact 75 is Normal. Exact 90 would be Elevated.

`L + 0.5 * E` is a multiple of one half, from 0 through 252. Exact 90 would require that quantity to be `0.90 * 252 = 226.8`, which is not a multiple of one half, so the formula cannot produce 90. With no ties, `L = 63` is exactly 25 and Low, and `L = 189` is exactly 75 and Normal. `L = 226` is `89.6825396...` and Elevated. `L = 227` is `90.0793650...` and High.

If today's RV21 is 0 and all 252 previous values are 0, then `L = 0` and `E = 252`. The percentile is `100 * (0 + 0.5 * 252) / 252 = 50`, and the regime is Normal. That path is not High.

Realised-volatility levels differ across markets, so an absolute number does not have one meaning for every asset. Ranking today's RV21 against that market's own trailing history makes the regime asset-relative. The rank does not assume a normal distribution, and it can be explained in a few seconds.

### History arithmetic

One RV21 uses 21 returns and therefore prices from `t-21` through `t`: 22 prices.

The regime needs today's RV21 and the previous 252 RV21 values, at `t-252` through `t-1`. The earliest of those, at `t-252`, uses prices from `t-273` through `t-252`. The full price set is `t-273` through `t`, which is 274 prices.

273 prices reach back only to `t-272`. The RV21 at `t-252` then has no price at `t-273`, so fewer than 252 previous RV21 values exist. 273 is insufficient for the complete regime. 274 is sufficient.

What Changed compares the complete regime at `t` with the complete regime at `t-1`. The regime at `t-1` needs a price at `(t-1)-273 = t-274`. Prices from `t-274` through `t` are 275 observations.

- At 274 the current full state can be available. The previous full state cannot. `change_status = unavailable` with `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`.
- At 275 both the current full state and the previous full state can be available.

The running validator rejects fewer than 274 observations with `DATA_INSUFFICIENT_HISTORY`. 273 and 272 both fail that gate. The 275 figure is the approved What Changed minimum. What Changed is not implemented, so 275 is not yet a validator gate.

### As-of contract

Volatility supports an exact `as_of_date`. For requested date `t`:

- use only that market
- require `t` to exist exactly, with no nearest-date substitution
- use no price after `t`
- today's RV21 uses only returns ending at `t`
- each reference RV21 uses only prices available on its own date
- the reference set ends at `t-1`
- today's RV21 does not enter its own percentile
- later rows are not borrowed to reach 274

### API

These names are implemented.

1. `calculate_rv21` takes exactly 22 adjusted closes in observation order, oldest first, and returns the decimal RV21. Fewer than 22 closes is `DATA_INSUFFICIENT_HISTORY`. More than 22 closes is `DATA_INVALID_VOLATILITY`. The function does not select a window from a longer series.
2. `classify_volatility(current_rv21, historical_rv21_values)` requires exactly 252 prior values. It returns a frozen classification with `historical_below_count`, `historical_equal_count`, `historical_reference_size`, `historical_percentile`, `volatility_regime`, and `reason_code`. Any other reference length is `DATA_INVALID_VOLATILITY`.
3. `calculate_volatility(prices, market_id, as_of_date)` selects one market, applies the as-of rule, and returns a frozen `VolatilityResult`.

`VolatilityResult` fields:

- `market_id`
- `as_of_date`
- `adjusted_close`
- `realized_volatility_21`
- `historical_below_count`, which is `L`
- `historical_equal_count`, which is `E`
- `historical_reference_size`, which is 252 in V1
- `historical_percentile`
- `volatility_regime`
- `reason_code`

The stored counts make the percentile auditable:

```text
historical_percentile = 100 * (historical_below_count + 0.5 * historical_equal_count) / historical_reference_size
```

There is no `reference_count` field. That name belonged to the withdrawn `<=` count. No confidence, signal strength, predicted volatility, or position size is included.

A non-finite, negative, boolean, string, or missing volatility input is `DATA_INVALID_VOLATILITY`. A non-finite, non-positive, boolean, string, or missing price is `DATA_INVALID_PRICE`. Fewer than 22 prices for standalone RV21, or fewer than 274 prices through the as-of date for the regime, is `DATA_INSUFFICIENT_HISTORY`.

### Future volatility research

These extensions are not part of V1 and are not implemented.

- EWMA and RiskMetrics-style volatility forecasting
- longer realised-volatility horizons, such as 63, 126, and 252 observations
- robust or multi-horizon volatility models
- implied volatility, once an appropriate options source exists

V1 measures realised volatility from past adjusted closes. A forecast estimates volatility that has not yet been observed. Implied volatility is a price from the options market. Those three jobs stay separate.

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

- 274 valid price observations are sufficient to calculate the latest complete market state.
- 273 observations are insufficient, because the volatility regime then has no price at `t-273`.
- 272 observations are also insufficient. Both fail with `DATA_INSUFFICIENT_HISTORY`. The validator enforces this 274 gate.

### What Changed minimum history

- 275 valid price observations are required to calculate both the latest complete state and the immediately previous complete state.
- At exactly 274 observations, the current state can succeed and the previous-session comparison is unavailable.

At exactly 274 observations the engine must not return:

```text
No market-state change since previous session
```

No valid comparison has been made. The result is:

```text
change_status = unavailable
```

with reason code `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`.

The sentence `No market-state change since previous session` is produced only when all three of these are true:

- at least 275 valid observations exist
- both the latest state and the previous state were calculated successfully
- none of the five categorical states changed

Those five states are the directional state, Trend, Momentum, Volatility, and Relative Strength. A difference in any of them is a categorical transition. Each transition names the instrument, the previous label, the new label, and the reason code.

This comparison is specified here and is not implemented. The running validator enforces 274 observations. The 275 What Changed minimum is not a validator gate.

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

The approved full current state requires 274 valid price observations on the shared date index for every required series.

The number is fixed by the volatility regime. RV21 at `t-252` needs the price at `t-273`, and the current price is at `t`, so the length is 274. Trend and Momentum need less history than that. A standalone RV21 needs 22 prices. The complete What Changed comparison needs 275.

The running validator rejects fewer than 274 observations with `DATA_INSUFFICIENT_HISTORY`. No partial state is published. 275 remains the What Changed minimum and is not enforced by the validator.

## Validation

Failures are explicit. No affected output is published with a substituted value. The same prices, configuration, and `evaluation_date` produce the same validation result.

Validation is deterministic and first-failure-wins. Configuration is validated before price data. Schema and value checks run before history and freshness. When one input violates more than one rule, exactly one error code is returned, using the order below.

Configuration order:

1. The columns are exactly `market_id`, `display_name`, `benchmark_id`, and `enabled`. A missing column is `CONFIG_MISSING_FIELD`. An unexpected column is `CONFIG_INVALID_COLUMNS`.
2. `market_id` values are unique. A duplicate is `CONFIG_DUPLICATE_MARKET`.
3. Each `enabled` value is a semantic boolean. Null or `pd.NA` is `CONFIG_MISSING_FIELD`. Any other non-boolean is `CONFIG_INVALID_FIELD`.
4. `market_id`, `display_name`, and `benchmark_id` are non-empty text without surrounding whitespace. Blank or whitespace-only text is `CONFIG_MISSING_FIELD`. Any other invalid text is `CONFIG_INVALID_FIELD`.
5. ACWI is present. Its absence is `CONFIG_MISSING_BENCHMARK`.
6. ACWI has `enabled = False`. An enabled ACWI is `CONFIG_BENCHMARK_ENABLED`.
7. Each required board market is present (`CONFIG_MISSING_MARKET`), enabled (`CONFIG_MARKET_DISABLED`), and uses `benchmark_id = ACWI` (`CONFIG_WRONG_BENCHMARK`). The required board markets are SPY, QQQ, IWM, EWU, EWG, EWJ, and EEM.
8. Every `benchmark_id` names a configured `market_id`. An unknown reference is `CONFIG_UNKNOWN_BENCHMARK`.
9. Every configured market, including disabled extra markets and ACWI, has `benchmark_id = ACWI`. Any other reference is `CONFIG_WRONG_BENCHMARK`.

Price-data order, after configuration has succeeded:

1. The columns are exactly `date`, `market_id`, and `adjusted_close`. A missing or unexpected column is `DATA_INVALID_COLUMNS`.
2. Rows are checked in input order. Within a row the order is `date` (`DATA_INVALID_DATE`), then `market_id` (`DATA_UNKNOWN_MARKET` when the identifier is blank or not text), then `adjusted_close` (`DATA_MISSING_VALUE` or `DATA_INVALID_PRICE`).
3. A `market_id` that is not in the configuration is `DATA_UNKNOWN_MARKET`.
4. A repeated `(date, market_id)` is `DATA_DUPLICATE_DATE`, including when the two prices are equal.
5. A required instrument with no rows is `DATA_MISSING_MARKET`.
6. A required instrument whose date set differs from the shared date index is `DATA_DATE_INDEX_MISMATCH`.
7. Fewer than 274 shared observations is `DATA_INSUFFICIENT_HISTORY`.
8. A latest shared observation later than `evaluation_date` is `DATA_FUTURE_DATE`. Future rows are not dropped.
9. A latest shared observation 6 or more calendar days before `evaluation_date` is `DATA_STALE`.

| Condition | Reason code |
|---|---|
| Latest complete observation is later than `evaluation_date` | `DATA_FUTURE_DATE` |
| Latest complete observation is more than 5 calendar days before `evaluation_date` | `DATA_STALE` |
| A required instrument has no rows | `DATA_MISSING_MARKET` |
| A required instrument is present but its dates differ from the shared index | `DATA_DATE_INDEX_MISMATCH` |
| More than one row exists for the same `market_id` and `date` | `DATA_DUPLICATE_DATE` |
| Fewer than 274 valid observations through the analysis date | `DATA_INSUFFICIENT_HISTORY` |
| `adjusted_close` is non-numeric, non-finite, or not greater than 0 | `DATA_INVALID_PRICE` |
| `adjusted_close` is blank or missing | `DATA_MISSING_VALUE` |

Duplicate keys fail even when the two prices are equal. Sorting the returned frame by `date` and then `market_id` is canonicalisation, not financial-data repair.

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

Phase 1A validation codes, all reachable from the validator:

- `CONFIG_BENCHMARK_ENABLED`
- `CONFIG_DUPLICATE_MARKET`
- `CONFIG_INVALID_COLUMNS`
- `CONFIG_INVALID_FIELD`
- `CONFIG_MARKET_DISABLED`
- `CONFIG_MISSING_BENCHMARK`
- `CONFIG_MISSING_FIELD`
- `CONFIG_MISSING_MARKET`
- `CONFIG_UNKNOWN_BENCHMARK`
- `CONFIG_WRONG_BENCHMARK`
- `DATA_DATE_INDEX_MISMATCH`
- `DATA_DUPLICATE_DATE`
- `DATA_FUTURE_DATE`
- `DATA_INSUFFICIENT_HISTORY`
- `DATA_INVALID_COLUMNS`
- `DATA_INVALID_DATE`
- `DATA_INVALID_PRICE`
- `DATA_MISSING_MARKET`
- `DATA_MISSING_VALUE`
- `DATA_STALE`
- `DATA_UNKNOWN_MARKET`

Specified for Volatility calculation, and not a regime label:

- `DATA_INVALID_VOLATILITY`

Specified for the later What Changed phase, and not current behaviour:

- `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`

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
