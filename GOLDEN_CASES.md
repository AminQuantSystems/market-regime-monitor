# Golden acceptance cases

**Status:** Trend cases below are the hand-checked inputs for `tests/test_trend.py`. Later instruments remain documentation until their phase is authorised.

Each case is constructed so the expected result can be checked by hand. Price comparisons use the approved exact rules, with no epsilon. Unless a case says otherwise, ACWI's 63-observation return is 0, and only the named prices differ from a flat series.

Trend constructions use 200 observations. The last observation is `t`. SMA50 is the mean of `t-49` through `t`. SMA200 is the mean of `t-199` through `t`.

## 1. Every Trend category

### 1a. Score +2

- `t-199` through `t-50`: 150 observations at 80
- `t-49` through `t-1`: 49 observations at 100
- price at `t`: 130

```text
SMA50 = (49 × 100 + 130) / 50 = 100.6
SMA200 = (150 × 80 + 49 × 100 + 130) / 200 = 85.15
130 > 100.6 > 85.15
```

Expected: price 130, SMA50 100.6, SMA200 85.15, score +2, Strong Up, `TREND_STRONG_UP_ALIGNMENT`.

### 1b. Score +1

- `t-199` through `t-50`: 150 observations at 50
- `t-49` through `t-1`: 49 observations at 100
- price at `t`: 90

```text
SMA50 = (49 × 100 + 90) / 50 = 99.8
SMA200 = (150 × 50 + 49 × 100 + 90) / 200 = 62.45
90 > 62.45, and 90 > 99.8 is false
```

Expected: price 90, SMA50 99.8, SMA200 62.45, score +1, Up, `TREND_UP_ABOVE_200`.

### 1c. Score -1

- `t-199` through `t-50`: 150 observations at 120
- `t-49` through `t-1`: 49 observations at 100
- price at `t`: 110

```text
SMA50 = (49 × 100 + 110) / 50 = 100.2
SMA200 = (150 × 120 + 49 × 100 + 110) / 200 = 115.05
110 < 115.05, and 110 < 100.2 is false
```

Expected: price 110, SMA50 100.2, SMA200 115.05, score -1, Down, `TREND_DOWN_BELOW_200`.

### 1d. Score -2

- `t-199` through `t-50`: 150 observations at 150
- `t-49` through `t-1`: 49 observations at 120
- price at `t`: 100

```text
SMA50 = (49 × 120 + 100) / 50 = 119.6
SMA200 = (150 × 150 + 49 × 120 + 100) / 200 = 142.4
100 < 119.6 < 142.4
```

Expected: price 100, SMA50 119.6, SMA200 142.4, score -2, Strong Down, `TREND_STRONG_DOWN_ALIGNMENT`.

## 2. Trend equality at SMA200

Two hundred observations, each `adjusted_close` equal to 100.

```text
SMA50 = 100
SMA200 = 100
price == SMA200
```

Expected: price 100, SMA50 100, SMA200 100, score 0, Neutral, `TREND_NEUTRAL_AT_200`. The +2 and -2 chains both fail because their inequalities are strict.

### Additional equality: SMA50 == SMA200 while price is above SMA200

This is not a sixth trend score. It locks the fall-through from the strict +2 chain.

- `t-199` through `t-50`: 150 observations at 100
- `t-49` through `t-2`: 48 observations at 100
- `t-1`: 90
- price at `t`: 110

```text
SMA50 = (48 × 100 + 90 + 110) / 50 = 100
SMA200 = (150 × 100 + 48 × 100 + 90 + 110) / 200 = 100
110 > 100, and SMA50 > SMA200 is false
```

Expected: price 110, SMA50 100, SMA200 100, score +1, Up, `TREND_UP_ABOVE_200`.

### Price equal to SMA50 while price is above SMA200

- `t-199` through `t-50`: 150 observations at 50
- `t-49` through `t`: 50 observations at 100

```text
SMA50 = 100
SMA200 = (150 × 50 + 50 × 100) / 200 = 62.5
price == SMA50, so the strict +2 chain fails
100 > 62.5
```

Expected: price 100, SMA50 100, SMA200 62.5, score +1, Up, `TREND_UP_ABOVE_200`.

### Price equal to SMA50 while price is below SMA200

- `t-199` through `t-50`: 150 observations at 150
- `t-49` through `t`: 50 observations at 100

```text
SMA50 = 100
SMA200 = (150 × 150 + 50 × 100) / 200 = 137.5
price == SMA50, so the strict -2 chain fails
100 < 137.5
```

Expected: price 100, SMA50 100, SMA200 137.5, score -1, Down, `TREND_DOWN_BELOW_200`.

### SMA50 equal to SMA200 while price is below SMA200

- `t-199` through `t-2`: 198 observations at 100
- `t-1`: 110
- price at `t`: 90

```text
SMA50 = (48 × 100 + 110 + 90) / 50 = 100
SMA200 = (198 × 100 + 110 + 90) / 200 = 100
90 < 100, and SMA50 < SMA200 is false
```

Expected: price 90, SMA50 100, SMA200 100, score -1, Down, `TREND_DOWN_BELOW_200`.

A Trend calculation with 200 observations is accepted. 199 observations fail with `DATA_INSUFFICIENT_HISTORY`. An as-of date that is not in the market's series fails with `DATA_INVALID_DATE` and is not replaced by a neighbouring date. Rows after the as-of date are not inputs to either average.

## 3. Momentum Accelerating

```text
price_t = 121
price_(t-21) = 100
price_(t-63) = 110
R21 = 121 / 100 - 1 = 0.21
R63 = 121 / 110 - 1 = 0.10
P21 = ln(1.21) / 21
P63 = ln(1.10) / 63
P21 > P63
```

Expected: Accelerating, `MOMENTUM_ACCELERATING`.

## 4. Momentum Positive

```text
price_t = 200
price_(t-21) = 198
price_(t-63) = 100
R21 = 200 / 198 - 1 > 0
R63 = 200 / 100 - 1 = 1
P21 = ln(200 / 198) / 21
P63 = ln(2) / 63
P21 < P63
```

Expected: Positive, `MOMENTUM_POSITIVE`.

### Equal positive pace

```text
price_t = 27
price_(t-21) = 9
price_(t-63) = 1
R21 = 27 / 9 - 1 = 2
R63 = 27 / 1 - 1 = 26
P21 = ln(3) / 21
P63 = ln(27) / 63
```

27 = 3³ and 63 = 3 × 21, so the two paces are the same number. `math.log` evaluates them as equal.

Expected: Positive, `MOMENTUM_POSITIVE`. Equal pace is not Mixed and not Accelerating.

## 5. Momentum Mixed via opposite signs

```text
price_t = 100
price_(t-21) = 90
price_(t-63) = 110
R21 = 100 / 90 - 1 > 0
R63 = 100 / 110 - 1 < 0
```

Expected: Mixed, `MOMENTUM_MIXED`. Pace is not consulted.

The mirror, `price_t = 100`, `price_(t-21) = 110`, `price_(t-63) = 90`, has R21 < 0 and R63 > 0. That is also Mixed, `MOMENTUM_MIXED`.

## 6. Momentum Mixed via exact zero

```text
price_t = 100
price_(t-21) = 100
price_(t-63) = 80
R21 = 0
R63 = 100 / 80 - 1 = 0.25
```

Expected: Mixed, `MOMENTUM_MIXED`.

R63 = 0 is the same state. One construction is `price_t = 100`, `price_(t-21) = 80`, `price_(t-63) = 100`.

Both returns zero, a constant price over 63 observations, is the same state and the same reason code.

## 7. Momentum Negative

```text
price_t = 90
price_(t-21) = 91
price_(t-63) = 150
R21 = 90 / 91 - 1 < 0
R63 = 90 / 150 - 1 < 0
P21 = ln(90 / 91) / 21
P63 = ln(90 / 150) / 63
P21 > P63
```

The recent decline is slower than the medium-term decline, so the recent pace is less negative.

Expected: Negative, `MOMENTUM_NEGATIVE`.

### Equal negative pace

```text
price_t = 1
price_(t-21) = 3
price_(t-63) = 27
R21 = 1 / 3 - 1 < 0
R63 = 1 / 27 - 1 < 0
P21 = ln(1 / 3) / 21
P63 = ln(1 / 27) / 63
```

These paces are the same number. Expected: Negative, `MOMENTUM_NEGATIVE`.

## 8. Momentum Deteriorating

```text
price_t = 70
price_(t-21) = 100
price_(t-63) = 110
R21 = 70 / 100 - 1 = -0.30
R63 = 70 / 110 - 1 < 0
P21 = ln(0.70) / 21
P63 = ln(70 / 110) / 63
P21 < P63
```

The recent decline is faster.

Expected: Deteriorating, `MOMENTUM_DETERIORATING`.

A Momentum calculation with 64 observations is accepted. 63 observations fail with `DATA_INSUFFICIENT_HISTORY`. An as-of date that is not in the market's series fails and is not replaced. Rows after the as-of date do not enter either return or either pace.

## 9. Volatility percentile boundaries

The reference sample has 252 previous realised-volatility values. The current value is not one of them.

```text
percentile = 100 × count(previous <= current) / 252
```

| Count at or below the current value | Percentile | Expected regime | Reason code |
|---:|---:|---|---|
| 63 | 25 exactly | Low | `VOLATILITY_LOW` |
| 64 | 25.3968... | Normal | `VOLATILITY_NORMAL` |
| 189 | 75 exactly | Normal | `VOLATILITY_NORMAL` |
| 190 | 75.3968... | Elevated | `VOLATILITY_ELEVATED` |
| 226 | 89.6825... | Elevated | `VOLATILITY_ELEVATED` |
| 227 | 90.0793... | High | `VOLATILITY_HIGH` |

There is no integer count that produces percentile 90. The approved boundary is still exact: 90 would be Elevated, and the first attainable value above 90 is High.

Worked annualisation, separate from the percentile count. Twenty log returns alternate between +0.01 and -0.01. Their mean is 0 and their sum of squares is 0.002.

```text
sample standard deviation = sqrt(0.002 / 19)
annualised volatility = sqrt(0.002 / 19) × sqrt(252) = sqrt(0.504 / 19)
```

The divisor is 19 because the sample standard deviation uses `ddof=1`.

## 10. Relative-strength boundaries

ACWI prices of 100 at `t` and 100 at `t-63` make `ACWI_R63 = 0`. The asset difference then equals the asset's own R63.

| Asset price at `t` | Asset price at `t-63` | Difference | Expected state | Reason code |
|---:|---:|---:|---|---|
| 105 | 100 | +0.05 | Leader | `RELATIVE_STRENGTH_LEADER` |
| 104.9 | 100 | +0.049 | Strong | `RELATIVE_STRENGTH_STRONG` |
| 102 | 100 | +0.02 | Strong | `RELATIVE_STRENGTH_STRONG` |
| 100 | 100 | 0 | Neutral | `RELATIVE_STRENGTH_NEUTRAL` |
| 98 | 100 | -0.02 | Weak | `RELATIVE_STRENGTH_WEAK` |
| 95.1 | 100 | -0.049 | Weak | `RELATIVE_STRENGTH_WEAK` |
| 95 | 100 | -0.05 | Laggard | `RELATIVE_STRENGTH_LAGGARD` |

The continuous value, not only the category, is the ranking input for leaders and laggards.

## 11. Strong Up

Trend +2, Momentum Accelerating, Relative Strength Leader.

Expected: Strong Up, `STATE_STRONG_UP`. Volatility may be any regime and must not change this result.

## 12. Up with conflicting confirmation

Trend +2, Momentum Deteriorating, Relative Strength Leader.

Momentum direction is negative. Relative-strength direction is positive. Strong Up fails because momentum is not positive. Up matches because the trend is positive and relative strength is positive.

Expected: Up, `STATE_UP`.

## 13. Neutral because a positive trend is opposed by both confirmations

Trend +2, Momentum Negative, Relative Strength Laggard.

Both confirmation directions are negative. Up fails because neither is positive. Strong Up fails for the same reason. The trend is not negative, so Down and Strong Down fail.

Expected: Neutral, `STATE_NEUTRAL`.

## 14. Strong Down

Trend -2, Momentum Negative, Relative Strength Laggard.

Expected: Strong Down, `STATE_STRONG_DOWN`. Volatility must not change this result.

## 15. Down with conflicting confirmation

Trend -2, Momentum Positive, Relative Strength Weak.

Strong Down fails because momentum is not negative. Down matches because the trend is negative and relative strength is negative.

Expected: Down, `STATE_DOWN`.

## 16. 273 observations accepted

Every required series has the same 273 dates and a finite positive `adjusted_close` on each. `evaluation_date` equals the last date.

Expected: the run succeeds and publishes a full current state. A constant price of 100 on every series is a sufficient fixture:

- Trend score 0, `TREND_NEUTRAL_AT_200`
- Momentum Mixed, `MOMENTUM_MIXED`
- Relative strength 0, `RELATIVE_STRENGTH_NEUTRAL`
- current and previous realised volatilities are all 0, so the percentile is 100 and the regime is High, `VOLATILITY_HIGH`
- directional state Neutral, `STATE_NEUTRAL`

What Changed is unavailable. `change_status = unavailable` with reason code `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`.

The result must not be `No market-state change since previous session`. The previous date has only 272 observations, so no valid comparison has been made.

## 16b. 274 observations make both states available

The same aligned fixture with 274 observations per required series, and `evaluation_date` equal to the last date.

Expected: the current state and the previous state are both available for comparison. This case does not, by itself, require the categories to be identical.

## 16c. 274 observations with identical categories

Every required series is a constant `adjusted_close` of 100 across all 274 dates. `evaluation_date` equals the last date.

Expected: both states are calculated, every categorical label is unchanged, and the comparison text is exactly `No market-state change since previous session`.

On this constant panel the labels on both dates are Trend score 0, Momentum Mixed, Volatility High, Relative Strength Neutral, and directional state Neutral.

## 17. 272 observations rejected

The same aligned fixture with 272 observations per required series.

Expected: `DATA_INSUFFICIENT_HISTORY`. No directional state and no instrument state are published.

## 18. Staleness of exactly 5 calendar days accepted

A valid 273-observation panel whose latest date is 2026-03-01. `evaluation_date` is 2026-03-06.

Expected: the run succeeds. The age is 5 calendar days.

## 19. Staleness of 6 calendar days rejected

The same panel. `evaluation_date` is 2026-03-07.

Expected: `DATA_STALE`. No market state is published. The check uses `evaluation_date` and does not read a system clock.

## 20. Shared date index mismatch

SPY is present in the file. Every required series except SPY has a price on the latest shared date. SPY has no row on that date.

Expected: `DATA_DATE_INDEX_MISMATCH`. The engine does not fall back to an earlier date and does not forward-fill SPY.

The same code applies when a required series is missing its first date, missing an internal date, or carrying an extra date. It also applies when every required series has 273 rows but the date sets differ.

## 20b. Required market absent entirely

A required series has no rows in the file.

Expected: `DATA_MISSING_MARKET`. This code is not used for a series that is present on a different set of dates.

## 21. Duplicate date rejected

Two rows share `market_id = SPY` and the same date. The case is failed whether or not the two `adjusted_close` values are equal.

Expected: `DATA_DUPLICATE_DATE`.

## Additional validation fixtures

These are not extra regimes. They lock the remaining approved error codes.

- A blank `adjusted_close` fails with `DATA_MISSING_VALUE`.
- An `adjusted_close` of 0, a negative price, or a non-finite price fails with `DATA_INVALID_PRICE`.
- A latest observation later than `evaluation_date` fails with `DATA_FUTURE_DATE`. Future rows are not dropped to recover an earlier date.

## Configuration contract

The required enabled board markets are SPY, QQQ, IWM, EWU, EWG, EWJ, and EEM. Each uses `benchmark_id = ACWI` and `enabled = True`.

ACWI is mandatory. Its `benchmark_id` is `ACWI` and its `enabled` value is `False`. That self-reference keeps the schema uniform. ACWI relative strength is not a board-market result.

Every configured market, including a disabled extra market, uses `benchmark_id = ACWI`.

- ACWI with `enabled = True` fails with `CONFIG_BENCHMARK_ENABLED`.
- ACWI with a `benchmark_id` other than `ACWI` fails. An unknown reference fails with `CONFIG_UNKNOWN_BENCHMARK`. A known market other than ACWI fails with `CONFIG_WRONG_BENCHMARK`.
- An enabled extra market whose benchmark is not ACWI fails with `CONFIG_WRONG_BENCHMARK`, including when `enabled` is a pandas nullable boolean.
- A disabled extra market whose benchmark is not ACWI fails with `CONFIG_WRONG_BENCHMARK` when the reference is a configured market, and with `CONFIG_UNKNOWN_BENCHMARK` when it is not.
- `"True"`, `"False"`, `"yes"`, `"no"`, `1`, `0`, `1.0`, `0.0`, null, and `pd.NA` are not accepted `enabled` values.
- An object column of genuine Python booleans is accepted.
- Blank or whitespace-only `market_id`, `display_name`, or `benchmark_id` fails with `CONFIG_MISSING_FIELD`.
- Surrounding whitespace on those fields fails with `CONFIG_INVALID_FIELD`. The value is not trimmed and accepted.
