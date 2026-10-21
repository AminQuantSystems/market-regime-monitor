# Finance specification — approved V1 model

**Status:** owner-approved V1 finance rules.
Phase 1A implements deterministic validation of prices and configuration. Phase 1B implements Trend. Phase 1C implements Momentum. Phase 1D implements realised volatility. Phase 1F implements Benchmark Relative Performance, including the boundary classification tolerance. Phase 1G implements the Market Regime Snapshot as orchestration only. What Changed is specified and is not implemented. There is no composite directional regime.

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

ACWI is mandatory. It is the common V1 comparison benchmark and is required for every Benchmark Relative Performance calculation. It is not a normal board card. It does not receive a Benchmark Relative Performance classification against itself, and that result is not displayed as a board-market result. Using one common benchmark makes the board comparable. It does not mean ACWI is the mandate-specific performance benchmark for every regional market.

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

Momentum is not a buy or sell signal, a position size, a volatility-adjusted allocation, or a price forecast. R21 and R63 are not divided by volatility. Volatility and Benchmark Relative Performance stay separate instruments. Later portfolio construction may scale by volatility. V1 Momentum does not.

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

Momentum does not overwrite Trend. A Strong Up trend with Deteriorating momentum is a valid reading, as is a Strong Down trend with Accelerating momentum. The disagreement stays visible.

## V — Volatility

**Status:** implemented in `src/market_state/volatility.py`.

V1 Volatility is a backward-looking realised-movement magnitude instrument. It asks how large recent daily price movements have been relative to this market's own recent history.

It does not say whether the market is bullish or bearish. It is not expected future volatility, implied volatility, value at risk, expected loss, a position size, or a trade direction. Volatility carries no directional vote and does not alter the Trend reading. A high or low regime is not bullish or bearish.

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

## R — Benchmark Relative Performance

**Status:** implemented in `src/market_state/relative_performance.py`.

The permanent V1 name is Benchmark Relative Performance. The shorter label Relative Performance may be used on a later interface. The question it answers is: how has this market performed over the previous 63 trading observations relative to the common ACWI comparison benchmark? The earlier working name "relative strength" is withdrawn as the instrument name. That phrase is used in finance for RSI, cross-sectional momentum, a relative-price ratio, and peer ranking. This instrument is none of those.

The calculation is conventional active return: the asset's return minus the benchmark's return over the same horizon. That difference is the usual meaning of active return in institutional active-management terminology. Market Regime Monitor does not claim CFA approval, GIPS compliance, or MSCI methodology replication. It performs cross-market comparative analytics, not formal performance reporting.

ACWI is the common V1 comparison benchmark so every enabled market is placed on one relative-performance scale. That is analytically useful for this product. It is not a claim that ACWI is the formally appropriate performance benchmark for US large-cap equities, Nasdaq equities, UK equities, German equities, Japanese equities, or emerging markets. A formal benchmark is chosen for a mandate, an objective, and an asset universe. A future client implementation may configure mandate-specific benchmarks. That flexibility is outside V1.

V1 does not substitute a price ratio divided by the benchmark price ratio, a logarithmic relative-return spread, regression alpha, CAPM alpha, an information ratio, tracking-error-adjusted performance, volatility-normalised momentum, or a peer z-score. Those are different measures.

### Formula

Both series use `adjusted_close`. The horizon is 63 trading observations, including the latest session. `t-63` is the observation 63 places before `t`, not 63 calendar days. There is no one-month skip. That skip belongs to some equity momentum-factor methodologies and solves a different problem.

```text
asset_return_63 = asset_price_t / asset_price_(t-63) - 1
benchmark_return_63 = ACWI_price_t / ACWI_price_(t-63) - 1
active_return_63 = asset_return_63 - benchmark_return_63
```

The stored value is the decimal difference. It is not annualised. An active return of +0.04 means the asset outperformed the common comparison benchmark by 4 percentage points over the 63 observations. An active return of -0.05 means the asset underperformed that benchmark by 5 percentage points.

For ordinary positive prices the simple return is `price_t / price_(t-63) - 1`, and that finite value is what is stored and classified. It is not rounded first. `expm1(ln(price_t) - ln(price_(t-63)))` is the same real number and does not form the quotient. The implementation evaluates that form when the direct quotient is not a finite return strictly greater than -1. A non-finite result, or a result that collapses to -1 or below, is `DATA_INVALID_ACTIVE_RETURN`. A positive ending price is not silently treated as a total loss. Nothing is clipped, capped, or repaired. The direct simple return is the classified value whenever it is finite and strictly greater than -1, because that is the definition and because the authorised boundary prices then stay on the specified side of 0.05, 0.02, -0.02, and -0.05.

An asset return of +0.10 and an ACWI return of +0.06 produce +0.04. An asset return of -0.03 and an ACWI return of +0.02 produce -0.05.

The asset and the benchmark use the same start date, the same end date, the same 63-observation lookback, and the same adjusted-close convention. The panel validator already requires one shared date index for every required series. A standalone calculation must still fail if the asset and benchmark observations it needs are not aligned. It must not choose a nearby date, borrow a later row, fill a gap, or interpolate.

### Horizon

Sixty-three observations are about one trading quarter. The same medium horizon is already used by Momentum, and it is responsive enough for a market-regime monitor. Relative and cross-sectional momentum research often looks at multi-month performance, and institutional factor methodologies commonly use longer 6-month and 12-month horizons. Market Regime Monitor does not claim that 63 observations are a universal institutional momentum-factor standard. This is a responsive benchmark-relative market-state measurement.

### Benchmark

Every enabled board market uses `benchmark_id = ACWI`. ACWI is mandatory and is the common comparison benchmark. It is not a normal board market, and it does not receive this classification against itself. A direct request whose `market_id` is ACWI, or whose `market_id` equals `benchmark_id`, fails with `DATA_BENCHMARK_EXCLUDED`. It does not return a zero active return or Neutral. Any other `benchmark_id` fails with `CONFIG_WRONG_BENCHMARK`.

The current V1 universe is market proxies represented by `adjusted_close` series. ACWI is the same kind of proxy in the project data model. Until a production market-data source is selected, Market Regime Monitor does not claim that `market_id` ACWI is official MSCI index data, that the proxy reproduces the MSCI ACWI Index, or that ETF expenses, withholding taxes, tracking difference, or a vendor's corporate-action treatment match an official index. No vendor is selected in this phase.

Benchmark-relative comparison should use economically comparable total-return series. V1 uses `adjusted_close` as its total-return proxy. What that field contains depends on the eventual provider. Before any production or vendor integration, the project must verify and document split adjustment, cash-distribution adjustment, currency convention, corporate-action methodology, and whether the asset series and the benchmark series are economically comparable. Formal performance measurement is not claimed before that verification.

### Classification bands

The five bands are Market Regime Monitor product classifications. They make the active return readable at a glance. They are not CFA, MSCI, S&P, regulatory, or universal institutional thresholds.

| State | Rule | Reason code |
|---|---|---|
| Strong Outperform | active_return_63 >= +0.05 | `RELATIVE_PERFORMANCE_STRONG_OUTPERFORM` |
| Outperform | +0.02 <= active_return_63 < +0.05 | `RELATIVE_PERFORMANCE_OUTPERFORM` |
| Neutral | -0.02 < active_return_63 < +0.02 | `RELATIVE_PERFORMANCE_NEUTRAL` |
| Underperform | -0.05 < active_return_63 <= -0.02 | `RELATIVE_PERFORMANCE_UNDERPERFORM` |
| Strong Underperform | active_return_63 <= -0.05 | `RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM` |

The financial product thresholds are +5%, +2%, -2%, and -5%, stored as the decimals +0.05, +0.02, -0.02, and -0.05. The exact endpoints are:

- +0.05 is Strong Outperform
- +0.02 is Outperform
- 0 is Neutral
- -0.02 is Underperform
- -0.05 is Strong Underperform

The stored `active_return_63` keeps the full computed simple-return difference. It is not rounded and it is not overwritten.

Classification uses one numerical tolerance, and only there. If the computed active return is within `1e-12` return units of one of those four thresholds, it is classified as that exact threshold. The tolerance is absolute. The relative tolerance is 0. It is not applied to any other comparison, and it is not an investment materiality threshold, a wider neutral band, display rounding, or a trading tolerance. It exists because the same real percentage, written at two nominal price scales, can land a few units in the last place on opposite sides of a fixed decimal boundary. Away from those four thresholds the band comparisons are exact. The five intervals still cover every finite real number and do not overlap.

The formal labels are Strong Outperform, Outperform, Neutral, Underperform, and Strong Underperform. Leader, Strong, Weak, and Laggard are not classification labels. Those words imply a cross-sectional rank.

A later Market State Board may still show a separate Leaders / Laggards panel. That panel ranks enabled markets by the continuous `active_return_63` value, for example QQQ at +6.8 percent ahead of SPY at +2.7 percent. The ranking is not the five-way classification. ACWI is not ranked.

Relative Performance does not alter absolute Direction. A market can be Down, with Deteriorating momentum and High volatility, and still be Strong Outperform against ACWI. That reading means the market is falling on its own path and has still beaten the common comparison benchmark.

### No risk adjustment

V1 does not divide the active return by realised volatility, tracking error, or a standard deviation. It does not calculate an information ratio, a Sharpe ratio, or a regression alpha inside this instrument. Institutional momentum-factor methodologies may risk-adjust returns. Market Regime Monitor keeps the components separate:

- Trend is structural direction.
- Momentum is the market's own short and medium price pace.
- Volatility is realised movement magnitude.
- Benchmark Relative Performance is the benchmark-relative return.

A later strategy or portfolio layer may combine or risk-adjust these quantities. V1 does not.

### Distinct from Trend and Momentum

The instruments are allowed to disagree. The disagreement is information.

Momentum can be positive while Benchmark Relative Performance is Strong Underperform. An asset return of +5 percent over 63 sessions is positive on the asset's own path. If ACWI returned +10 percent, the active return is -5 percent. Momentum answers whether this market is moving positively or negatively on its own. Benchmark Relative Performance answers how it did versus ACWI.

Trend can be Strong Up while the asset underperforms ACWI. The asset's own price structure can be bullish while the global-equity benchmark rose faster. The two readings are not forced into agreement.

### History

A 63-observation return needs the price at `t` and the price at `t-63`. Standalone Benchmark Relative Performance therefore needs 64 aligned observations for the asset and 64 aligned observations for ACWI. 63 observations are insufficient.

The panel validator remains at 274 observations because the volatility regime is the longest current-state requirement. This design does not change that gate. The planned What Changed minimum remains 275.

### As-of date

At date `t`, the asset return uses `asset_t` and `asset_(t-63)`. The benchmark return uses `ACWI_t` and `ACWI_(t-63)`. No row after `t` may change the result. Both series must contain the exact as-of date, and the lagged observation must be the same date on both series. There is no nearest-date substitution, no future borrowing, no fill, and no interpolation. Future rows cannot be used to make 63 observations into 64.

### Failure behaviour

Where an existing public code already means the failure, the calculation reuses it. Two conditions need their own codes, because no earlier code means either of them: the requested market is the benchmark, and an active return cannot be represented as a usable finite number.

| Condition | Code |
|---|---|
| `market_id` is ACWI, or `market_id` equals `benchmark_id` | `DATA_BENCHMARK_EXCLUDED` |
| `benchmark_id` is not ACWI | `CONFIG_WRONG_BENCHMARK` |
| The requested market has no rows | `DATA_MISSING_MARKET` |
| ACWI has no rows | `DATA_MISSING_MARKET` |
| The as-of date is absent from the asset | `DATA_INVALID_DATE` |
| The as-of date is absent from ACWI | `DATA_INVALID_DATE` |
| A date is repeated on the asset or on ACWI | `DATA_DUPLICATE_DATE` |
| The latest 64 asset and ACWI date labels differ | `DATA_DATE_INDEX_MISMATCH` |
| Fewer than 64 observations through the as-of date | `DATA_INSUFFICIENT_HISTORY` |
| An endpoint adjusted close is missing, non-finite, or not greater than 0 | `DATA_INVALID_PRICE` |

The four endpoints are the asset and ACWI closes at `t` and at `t-63`. The panel validator already checks every price in the panel. The standalone calculation checks the endpoints it consumes. It does not replace the panel validator.

`DATA_BENCHMARK_EXCLUDED` names the market that was refused. It is not a classification label. `DATA_INVALID_ACTIVE_RETURN` is also used when `expm1` overflows or the simple return collapses to -1 or below.

### API

Implemented in `src/market_state/relative_performance.py`. The two functions stay independent of Trend, Momentum, and Volatility.

```text
classify_relative_performance(active_return_63)
calculate_relative_performance(prices, market_id, benchmark_id, as_of_date)
```

`classify_relative_performance` applies the five bands to one computed active return. `calculate_relative_performance` builds both 63-observation returns from aligned adjusted closes and then classifies their difference.

The result is immutable. Its fields are:

- `market_id`
- `benchmark_id`
- `as_of_date`
- `adjusted_close`
- `benchmark_adjusted_close`
- `asset_return_63`
- `benchmark_return_63`
- `active_return_63`
- `relative_performance_state`
- `reason_code`

Full precision is retained. There is no score, confidence, probability, predicted return, or position size, and there is no UI formatting in the result.

`classify_relative_performance` is a predicate on one active return. It does not rebuild that return from prices. A negative value and a huge finite value are valid inputs and fall through the bands. A non-finite, boolean, string, or missing value fails with `DATA_INVALID_ACTIVE_RETURN`. A raw arithmetic exception does not escape.

### Future benchmark-relative research

These constructions are outside V1 and are not implemented.

- 6-month benchmark-relative performance
- 12-month benchmark-relative performance
- one-month-lagged factor momentum
- cross-sectional ranking or z-scores as the classification itself
- risk-adjusted momentum
- active return divided by tracking error
- relative-price-ratio trend analysis
- mandate-specific benchmarks in place of the common ACWI comparison benchmark

Each of those answers a different question from the 63-observation arithmetic active return.

## Four market dimensions

Market Regime Monitor keeps four transparent dimensions:

- T — Trend
- M — Momentum
- V — Volatility
- R — Benchmark Relative Performance

There is no hidden composite score. An earlier design that built a fifth Directional Regime from Trend, Momentum, and Benchmark Relative Performance is withdrawn. Those three readings are not independent votes. Trend and Momentum both come from the same adjusted-close history, so weighting them together would count similar price behaviour twice.

Trend supplies structural Direction. Its states are Strong Up, Up, Neutral, Down, and Strong Down. A later interface may show that Trend state under the heading Direction. That heading is presentation only. There is no second direction calculation.

Momentum stays independently visible: Accelerating, Positive, Mixed, Negative, and Deteriorating. It describes recent price pace. It does not overwrite Trend.

Volatility stays independent: Low, Normal, Elevated, and High. It measures realised movement magnitude and carries no directional vote.

Benchmark Relative Performance stays independent: Strong Outperform, Outperform, Neutral, Underperform, and Strong Underperform. It compares the market with the common ACWI benchmark. It does not change absolute Direction.

Agreement and disagreement are shown rather than collapsed. These readings can stand together:

- Direction Strong Up, Momentum Deteriorating
- Direction Strong Down, Momentum Accelerating
- Direction Down, Momentum Deteriorating, Volatility High, Relative Performance Strong Outperform

The last reading is a market that is falling on its own path and has still outperformed ACWI.

The four states together are the descriptive regime signature, for example Strong Up / Accelerating / Elevated / Outperform. That is a tuple of transparent states. V1 does not turn it into one score, one probability, one hidden regime code, or a label such as Risk-On, Risk-Off, Goldilocks, Crisis, or Expansion. Those would be separate models.

### Market Regime Snapshot

Implemented in Phase 1G. `MarketRegimeSnapshot` is an orchestration and audit object, not a fifth model. `calculate_market_regime_snapshot` calls `calculate_trend`, `calculate_momentum`, `calculate_volatility`, and `calculate_relative_performance` once each. All four receive the same prices, the same market, and the same exact as-of date. Relative performance also receives `benchmark_id`. The ACWI check stays inside that instrument.

The snapshot stores:

- `market_id`
- `as_of_date`
- `trend`, a `TrendResult`
- `momentum`, a `MomentumResult`
- `volatility`, a `VolatilityResult`
- `relative_performance`, a `RelativePerformanceResult`

It does not flatten those results and it does not copy their formulas. Direction is `trend.trend_state`. There is no second direction calculation. If a component raises `MarketDataError`, that same error propagates and no snapshot is returned. The function does not call `validate_market_data` and it does not restate a second history minimum. The binding length is the volatility regime, so a complete snapshot needs 274 aligned observations. 273 observations fail with `DATA_INSUFFICIENT_HISTORY`.

A snapshot is one market at one as-of date. It does not contain the previous session. What Changed, when it exists, will compare two snapshots in a separate module.

Every stored value comes from one of the four result objects. That makes the assembly traceable to the instrument that calculated it. This is not independent regulatory validation. The project uses staged adversarial review and regression testing. It has not undergone independent bank model validation or regulatory approval.

The snapshot has no composite score, confidence, probability, AI regime, buy or sell instruction, recommendation, expected return, or position size.

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
- none of the four dimensions changed

Those four dimensions are Direction / Trend, Momentum, Volatility, and Benchmark Relative Performance. There is no composite-regime transition. A difference in any dimension is a categorical transition. Each transition names the dimension, the previous label, and the new label. Examples are Up to Strong Up, Positive to Accelerating, Normal to Elevated, and Neutral to Outperform.

A later primary board may show a compact mark that a dimension changed. If space forces a presentation order, it is Direction, then Momentum, then Volatility, then Relative Performance. That order is display priority only. It is not a financial weight and it is not a severity score.

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

The number is fixed by the volatility regime. RV21 at `t-252` needs the price at `t-273`, and the current price is at `t`, so the length is 274. Trend needs 200 observations. Momentum needs 64. Standalone Benchmark Relative Performance needs 64 aligned observations on the asset and on ACWI, because the price at `t-63` is required. A standalone RV21 needs 22 prices. The complete What Changed comparison needs 275. The 64-observation relative-performance requirement does not change the 274 panel gate.

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
- `RELATIVE_PERFORMANCE_STRONG_OUTPERFORM`
- `RELATIVE_PERFORMANCE_OUTPERFORM`
- `RELATIVE_PERFORMANCE_NEUTRAL`
- `RELATIVE_PERFORMANCE_UNDERPERFORM`
- `RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM`

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

Specified for Benchmark Relative Performance calculation, and not regime labels:

- `DATA_BENCHMARK_EXCLUDED`
- `DATA_INVALID_ACTIVE_RETURN`

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
- A composite directional regime, a hidden regime score, or a label such as Risk-On, Risk-Off, Goldilocks, Crisis, or Expansion
