# Golden acceptance cases

**Status:** Trend cases below are the hand-checked inputs for `tests/test_trend.py`. Momentum cases are the hand-checked inputs for `tests/test_momentum.py`. Volatility cases are the hand-checked inputs for `tests/test_volatility.py`. Benchmark Relative Performance cases are the hand-checked inputs for `tests/test_relative_performance.py`.

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

## 9. Volatility design cases

These cases are the hand-checked Volatility inputs. RV21 is the zero-mean root-mean-square of 21 log returns, annualised with 252. Each log return is `ln(price_i) - ln(price_(i-1))`. The percentile is a midrank of the previous 252 RV21 values. Today's RV21 is not in that set.

```text
r_i = ln(price_i / price_(i-1))
RV21 = sqrt( (252 / 21) * sum(r_i^2) ) = sqrt( 252 * mean(r_i^2) )
L = count(previous_rv21 < current_rv21)
E = count(previous_rv21 == current_rv21)
percentile = 100 * (L + 0.5 * E) / 252
```

### 9a. Constant prices

Every price is 100. Every log return is 0. The sum of squares is 0.

```text
RV21 = 0
```

### 9b. Constant log-return magnitude

Each of the 21 log returns is `+0.01`. The sum of squares is `21 * 0.0001 = 0.0021`.

```text
RV21 = sqrt( (252 / 21) * 0.0021 ) = sqrt(0.0252) = 0.01 * sqrt(252)
```

One price construction is a geometric path whose exact step ratio is `e^0.01`. In real arithmetic every log return is 0.01. A later test compares the computed float with `pytest.approx` and does not use that approximation to choose a regime.

### 9c. Alternating sign, same magnitude

The 21 log returns alternate `+0.01, -0.01`, starting at `+0.01`. Because 21 is odd, eleven returns are positive and ten are negative. Their mean is `0.01 / 21`, which is not zero. The squares are still `0.0001` each, so the sum of squares is `0.0021` and RV21 equals case 9b. The approved formula does not subtract that mean.

### 9d. Standalone history

22 prices are sufficient for one RV21. 21 prices are insufficient.

### 9e. Complete regime history

274 prices are sufficient for today's RV21 plus the previous 252 RV21 values. The earliest reference value, at `t-252`, uses the price at `t-273`. 273 prices do not contain that price, so the complete regime is unavailable.

### 9f. Percentile boundaries

No-tie cases have `E = 0`, so the percentile is `100 * L / 252`.

| Case | L | E | Effective count | Percentile | Regime | Reason code |
|---|---:|---:|---:|---|---|---|
| A | 63 | 0 | 63 | 25 exactly | Low | `VOLATILITY_LOW` |
| B | 64 | 0 | 64 | `6400 / 252 = 25.3968253...` | Normal | `VOLATILITY_NORMAL` |
| C | 189 | 0 | 189 | 75 exactly | Normal | `VOLATILITY_NORMAL` |
| D | 190 | 0 | 190 | `19000 / 252 = 75.3968253...` | Elevated | `VOLATILITY_ELEVATED` |
| E | 226 | 0 | 226 | `22600 / 252 = 89.6825396...` | Elevated | `VOLATILITY_ELEVATED` |
| F | 227 | 0 | 227 | `22700 / 252 = 90.0793650...` | High | `VOLATILITY_HIGH` |
| G | 0 | 252 | 126 | 50 exactly | Normal | `VOLATILITY_NORMAL` |
| H | 62 | 2 | 63 | 25 exactly | Low | `VOLATILITY_LOW` |
| I | 188 | 2 | 189 | 75 exactly | Normal | `VOLATILITY_NORMAL` |
| J | 252 | 0 | 252 | 100 exactly | High | `VOLATILITY_HIGH` |
| K | 0 | 0 | 0 | 0 exactly | Low | `VOLATILITY_LOW` |

Case G is the constant series: today's RV21 is 0 and all 252 previous values are 0. Half weight on every tied value gives percentile 50 and Normal. It is not High.

Case H reaches the Low boundary through ties: `62 + 0.5 * 2 = 63`. Case I reaches the Normal boundary through ties: `188 + 0.5 * 2 = 189`.

Case J is a current value strictly above every historical value. Case K is a current value strictly below every historical value. Today's value is not added to the 252.

`L + 0.5 * E` cannot equal 226.8, so the formula cannot produce percentile 90. A literal 90 would be Elevated. Case F is the first listed no-tie value above 90, and it is High.

Every real percentile falls in exactly one band: at or below 25, above 25 through 75, above 75 through 90, or above 90.

### 9g. Today's value is excluded

The reference length stays 252. If all 252 previous values are 0.10 and today's RV21 is 0.50, then `L = 252`, `E = 0`, and the percentile is 100. Today's 0.50 is not added to the reference set. That is case J.

### 9h. As-of, isolation, and caller contract

An exact as-of date is required. A later block of extreme adjusted closes does not change the RV21, the percentile, the regime, or the reason code at the original date. Another market's prices in the same frame do not change the requested market. The same history, market, and as-of date return the same result. The caller's frame is not mutated.

### 9i. 274 current state, 275 What Changed

At 274 prices the current full state can be calculated, and the previous full state cannot. The change status is `UNAVAILABLE` with `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`. The text is not `No market-state change since previous session`.

At 275 prices both states can be calculated. A constant `adjusted_close` of 100 across those 275 dates keeps every category unchanged, including Volatility Normal, so that sentence is allowed only in that complete comparison.

## 10. Benchmark Relative Performance

Verified by `tests/test_relative_performance.py`. The earlier formal labels Leader, Strong, Weak, and Laggard are withdrawn. The classification labels are Strong Outperform, Outperform, Neutral, Underperform, and Strong Underperform.

Each return is the simple 63-observation adjusted-close return, `price_t / price_(t-63) - 1`. Active return is the asset return minus the ACWI return. Classification uses that computed difference. There is no epsilon and no rounding before the comparison. In the price rows, both series are 100 at `t-63`. The active return in real arithmetic is then `(asset price at t - ACWI price at t) / 100`. The stored measurement keeps full precision. Classification treats a computed active return within `1e-12` of +0.05, +0.02, -0.02, or -0.05 as that exact product threshold. The stored active return is not replaced by the threshold. ACWI is the common comparison benchmark, not a claim that it is each market's mandate benchmark.

A separate Leaders / Laggards panel, if built later, ranks enabled markets by the continuous active return. That ranking is not these five labels.

### 10a. Strong Outperform

Asset return +10 percent, from 110 at `t` and 100 at `t-63`. ACWI return +4 percent, from 104 and 100. Active return +6 percent.

Expected: Strong Outperform, `RELATIVE_PERFORMANCE_STRONG_OUTPERFORM`.

### 10b. Exact +5 percent

Asset return +10 percent, from 110 and 100. ACWI return +5 percent, from 105 and 100. Active return +5 percent.

Expected: Strong Outperform, `RELATIVE_PERFORMANCE_STRONG_OUTPERFORM`. +0.05 is the closed upper boundary.

### 10c. Outperform

Asset return +6 percent, from 106 and 100. ACWI return +3 percent, from 103 and 100. Active return +3 percent.

Expected: Outperform, `RELATIVE_PERFORMANCE_OUTPERFORM`.

### 10d. Exact +2 percent

Asset return +5 percent, from 105 and 100. ACWI return +3 percent, from 103 and 100. Active return +2 percent.

Expected: Outperform, `RELATIVE_PERFORMANCE_OUTPERFORM`. +0.02 is the closed lower boundary of Outperform.

### 10e. Neutral, asset ahead

Asset return +4 percent, from 104 and 100. ACWI return +3 percent, from 103 and 100. Active return +1 percent.

Expected: Neutral, `RELATIVE_PERFORMANCE_NEUTRAL`.

### 10f. Exact zero

Asset return +3 percent and ACWI return +3 percent. Both series use 103 at `t` and 100 at `t-63`. The two returns are the same number, so the active return is exactly 0.

Expected: Neutral, `RELATIVE_PERFORMANCE_NEUTRAL`.

### 10g. Neutral, asset behind

Asset return +2 percent, from 102 and 100. ACWI return +3 percent, from 103 and 100. Active return -1 percent.

Expected: Neutral, `RELATIVE_PERFORMANCE_NEUTRAL`.

### 10h. Exact -2 percent

Asset return +1 percent, from 101 and 100. ACWI return +3 percent, from 103 and 100. Active return -2 percent.

Expected: Underperform, `RELATIVE_PERFORMANCE_UNDERPERFORM`. -0.02 is the closed upper boundary of Underperform.

### 10i. Underperform

Asset return 0 percent, from 100 and 100. ACWI return +3 percent, from 103 and 100. Active return -3 percent.

Expected: Underperform, `RELATIVE_PERFORMANCE_UNDERPERFORM`.

### 10j. Exact -5 percent

Asset return -2 percent, from 98 and 100. ACWI return +3 percent, from 103 and 100. Active return -5 percent.

Expected: Strong Underperform, `RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM`. -0.05 is the closed boundary.

### 10k. Strong Underperform

Asset return -5 percent, from 95 and 100. ACWI return +3 percent, from 103 and 100. Active return -8 percent.

Expected: Strong Underperform, `RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM`.

### 10l. Both negative, asset ahead of the benchmark

Asset return -2 percent, from 98 and 100. ACWI return -8 percent, from 92 and 100. Active return +6 percent.

Expected: Strong Outperform, `RELATIVE_PERFORMANCE_STRONG_OUTPERFORM`.

The asset fell. It still outperformed ACWI. Benchmark Relative Performance is not the absolute direction of the market.

### 10m. Both positive, asset behind the benchmark

Asset return +5 percent, from 105 and 100. ACWI return +10 percent, from 110 and 100. Active return -5 percent.

Expected: Strong Underperform, `RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM`.

The asset rose. It still underperformed ACWI. Momentum can remain positive on the asset's own return. There is no requirement that the two instruments agree.

### 10n. 64 observations accepted

The asset and ACWI share the same 64 dates through the as-of date, with a finite positive adjusted close on every consumed endpoint. The return uses the last close and the close 63 observations earlier.

Expected: the calculation succeeds.

### 10o. 63 observations rejected

The same two series, aligned, with 63 observations through the as-of date.

Expected: `DATA_INSUFFICIENT_HISTORY`. The price at `t-63` does not exist. No relative-performance label is published. The panel validator's 274 gate is a separate rule and is unchanged.

### 10p. Exact as-of date

The requested date is missing from the asset, or missing from ACWI, or is a neighbouring date that does exist.

Expected: `DATA_INVALID_DATE`. The calculation does not move to the nearest date.

### 10q. Future observations ignored

Rows dated after the as-of date are present, including extreme adjusted closes. The history through the as-of date is otherwise valid.

Expected: those later rows do not change either return, the active return, the state, or the reason code. A 63-observation prefix plus future rows is still `DATA_INSUFFICIENT_HISTORY`. Future rows are not borrowed to complete the 64.

### 10r. Another market does not contaminate the pair

The frame also contains another market with extreme adjusted closes. The requested asset and ACWI are unchanged.

Expected: the other market does not change the asset return, the ACWI return, the active return, the state, or the reason code.

### 10s. Caller input is not mutated

The same frame is used for a successful calculation and for a failing one.

Expected: the caller's rows are unchanged in both cases.

### 10t. Deterministic repeat

The same prices, asset, benchmark, and as-of date are calculated twice.

Expected: the two results are identical.

A request whose market is ACWI fails with `DATA_BENCHMARK_EXCLUDED` and does not return Neutral. A `benchmark_id` other than ACWI fails with `CONFIG_WRONG_BENCHMARK`. A missing asset or a missing ACWI fails with `DATA_MISSING_MARKET`. Date sets that differ through the as-of date fail with `DATA_DATE_INDEX_MISMATCH`. A duplicate date fails with `DATA_DUPLICATE_DATE`. An invalid endpoint adjusted close fails with `DATA_INVALID_PRICE`.

## 11. Withdrawn composite direction

An earlier design combined Trend, Momentum, and Benchmark Relative Performance into one Directional Regime. That design is withdrawn. It is not an acceptance case. Direction is the Trend state. Momentum, Volatility, and Benchmark Relative Performance stay visible beside it.

These four readings are valid together and are not collapsed:

- Trend Strong Up and Momentum Deteriorating
- Trend Strong Down and Momentum Accelerating
- Trend Down, Momentum Deteriorating, Volatility High, and Benchmark Relative Performance Strong Outperform

The regime signature is the tuple of the four states, for example Strong Up / Accelerating / Elevated / Outperform. There is no fifth score.

## 12. Market regime snapshot

274 aligned dates. SPY has 273 closes at 128 and a final close of 144. ACWI has 273 closes at 128 and a final close of 160. The as-of date is the final date.

Hand checks, before any production call:

- SMA50 = (49 × 128 + 144) / 50 = 128.32. SMA200 = (199 × 128 + 144) / 200 = 128.08. The final close 144 is above both, and SMA50 is above SMA200. Trend is Strong Up, `TREND_STRONG_UP_ALIGNMENT`.
- The 21-observation and 63-observation price ratios are both 144/128 = 1.125. Both returns are +0.125. The same positive ratio divided by 21 is a faster pace than the same ratio divided by 63. Momentum is Accelerating, `MOMENTUM_ACCELERATING`.
- Every historical RV21 window ends before the final close, so it sits on the flat 128 closes and its RV21 is 0. The current window contains the single jump, so its RV21 is positive. L = 252, E = 0, percentile = 100. Volatility is High, `VOLATILITY_HIGH`.
- Asset return 0.125 minus ACWI return 0.25 is active return −0.125. Benchmark Relative Performance is Strong Underperform, `RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM`.

The snapshot keeps those four results. It does not replace the disagreement between Strong Up and Strong Underperform.

### 12b. Strong Up with deteriorating momentum

The same 274 dates. ACWI is 100 on every date. SPY is 100 except the close 63 observations before the end, which is 400, the close 21 observations before the end, which is 300, and the final close, which is 200.

- SMA50 = (48 × 100 + 300 + 200) / 50 = 106. SMA200 = (197 × 100 + 400 + 300 + 200) / 200 = 103. Final close 200 > 106 > 103. Trend is Strong Up, `TREND_STRONG_UP_ALIGNMENT`.
- R21 = 200/300 − 1 < 0. R63 = 200/400 − 1 = −0.5. (2/3)³ = 8/27 < 1/2, so the recent pace is more negative than the 63-observation pace. Momentum is Deteriorating, `MOMENTUM_DETERIORATING`.
- Active return = −0.5. Benchmark Relative Performance is Strong Underperform, `RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM`.

The snapshot retains Strong Up and Deteriorating together. Volatility stays the volatility instrument's own result.

A component result whose market id, as-of date, or benchmark id contradicts the request does not become a snapshot. The orchestration error is `MarketRegimeError` with `REGIME_COMPONENT_MISMATCH`.

## 13. What Changed

Design only. These cases are not implemented and have no Python tests yet. What Changed compares categorical labels on two snapshots. It does not calculate finance.

1. **274 observations.** The current snapshot is valid. The change status is `UNAVAILABLE`. The reason is `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`. The previous snapshot is null, the transition list is empty, and the current snapshot is present. The result does not say that nothing changed.

2. **275 observations, same four labels.** The status is `UNCHANGED`. The transition list is empty. The reason is `CHANGE_NO_STATE_CHANGE`. Drill-down may say `No market-state change since previous session`. The primary column is `—`.

3. **Direction only.** Up becomes Strong Up. One transition, dimension `direction`. Status `CHANGED`, reason `CHANGE_STATE_CHANGED`. The primary column is `D`.

4. **Momentum only.** Positive becomes Accelerating. Dimension `momentum`. The primary column is `M`.

5. **Volatility only.** Normal becomes Elevated. Dimension `volatility`. The primary column is `V`. The result does not call the move better or worse.

6. **Relative Performance only.** Neutral becomes Outperform. Dimension `relative_performance`. The primary column is `R`. The result does not treat that as an absolute direction.

7. **Direction and Momentum.** Both transitions are kept, direction first, then momentum. The primary column is `D M`.

8. **All four dimensions.** Up to Strong Up, Positive to Accelerating, Normal to Elevated, and Neutral to Outperform. All four transitions are kept in the order direction, momentum, volatility, relative performance. The primary column is `D M V R`.

9. **Numbers move inside the same labels.** RV21 moves while Volatility stays Normal, and the active return moves while Relative Performance stays Outperform. The other labels are also unchanged. The status is `UNCHANGED` and the transition list is empty.

10. **Friday then Monday.** The observation series contains Friday and the next row is Monday. The current date is Monday. The previous date is Friday, the preceding observation, not Sunday and not a calendar subtraction.

11. **Rows after the as-of date.** Extreme later prices on the requested market, ACWI, and another market leave the current and previous change result equal.

12. **Another market.** Extreme prices on an unrelated market leave the requested change result equal.

13. **Caller input.** A successful comparison and a failing comparison leave the caller's frame unchanged.

14. **Repeat.** The same prices, market, benchmark, and as-of date produce the same change result.

15. **Wrong benchmark.** A benchmark other than ACWI propagates `CONFIG_WRONG_BENCHMARK`. It does not become `UNAVAILABLE`.

16. **Invalid current as-of date.** A missing as-of date propagates `DATA_INVALID_DATE`. It does not become `UNAVAILABLE`.

## 16. Validator: 274 observations accepted

Every required series has the same 274 dates and a finite positive `adjusted_close` on each. `evaluation_date` equals the last date.

Expected: the panel is accepted. This is the full current-state minimum. What Changed is not implemented. At 274 the previous full state cannot be calculated, so a later comparison must not say `No market-state change since previous session`.

## 16b. Approved current state at 274

The same aligned fixture with 274 observations per required series, and `evaluation_date` equal to the last date.

Expected: the current full state can be calculated. The previous full state cannot. The change status is `UNAVAILABLE` with `CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY`.

The result must not be `No market-state change since previous session`.

## 16c. 275 observations with identical categories

Every required series is a constant `adjusted_close` of 100 across all 275 dates. `evaluation_date` equals the last date.

Expected once What Changed exists: both states are calculated, every categorical label is unchanged, the status is `UNCHANGED`, the transition list is empty, and the drill-down text is exactly `No market-state change since previous session`. The primary column is `—`.

On this constant panel the labels on both dates are Trend Neutral, score 0, Momentum Mixed, Volatility Normal, and Benchmark Relative Performance Neutral. The active return is 0 because every market, including ACWI, is unchanged. Volatility is Normal because every RV21 is 0, `L = 0`, `E = 252`, and the percentile is 50. None of the four dimensions changed.

## 17. 273 and 272 observations rejected

The same aligned fixture with 273 observations per required series, and the same fixture with 272.

Expected: `DATA_INSUFFICIENT_HISTORY`. No instrument state is published. 273 prices do not contain the price at `t-273`, so the complete volatility regime cannot be calculated.

## 18. Staleness of exactly 5 calendar days accepted

A panel the validator accepts, with 274 observations whose latest date is 2026-03-01. `evaluation_date` is 2026-03-06.

Expected: the run succeeds. The age is 5 calendar days.

## 19. Staleness of 6 calendar days rejected

The same panel. `evaluation_date` is 2026-03-07.

Expected: `DATA_STALE`. No market state is published. The check uses `evaluation_date` and does not read a system clock.

## 20. Shared date index mismatch

SPY is present in the file. Every required series except SPY has a price on the latest shared date. SPY has no row on that date.

Expected: `DATA_DATE_INDEX_MISMATCH`. The engine does not fall back to an earlier date and does not forward-fill SPY.

The same code applies when a required series is missing its first date, missing an internal date, or carrying an extra date. It also applies when every required series has the same row count but the date sets differ.

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

ACWI is mandatory. Its `benchmark_id` is `ACWI` and its `enabled` value is `False`. That self-reference keeps the schema uniform. ACWI does not receive a Benchmark Relative Performance classification against itself.

Every configured market, including a disabled extra market, uses `benchmark_id = ACWI`.

- ACWI with `enabled = True` fails with `CONFIG_BENCHMARK_ENABLED`.
- ACWI with a `benchmark_id` other than `ACWI` fails. An unknown reference fails with `CONFIG_UNKNOWN_BENCHMARK`. A known market other than ACWI fails with `CONFIG_WRONG_BENCHMARK`.
- An enabled extra market whose benchmark is not ACWI fails with `CONFIG_WRONG_BENCHMARK`, including when `enabled` is a pandas nullable boolean.
- A disabled extra market whose benchmark is not ACWI fails with `CONFIG_WRONG_BENCHMARK` when the reference is a configured market, and with `CONFIG_UNKNOWN_BENCHMARK` when it is not.
- `"True"`, `"False"`, `"yes"`, `"no"`, `1`, `0`, `1.0`, `0.0`, null, and `pd.NA` are not accepted `enabled` values.
- An object column of genuine Python booleans is accepted.
- Blank or whitespace-only `market_id`, `display_name`, or `benchmark_id` fails with `CONFIG_MISSING_FIELD`.
- Surrounding whitespace on those fields fails with `CONFIG_INVALID_FIELD`. The value is not trimmed and accepted.
