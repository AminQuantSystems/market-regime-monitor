# Interface concept

**Status:** design specified and implemented. The branded board, row selection, detail panel, CSV upload controls, and Return to Demo are the V1 release candidate described in `PROJECT_STATE.md`. Visual tokens are in `MEEM_DESIGN_SYSTEM.md` and `MEEM_DESIGN_TOKENS.json`. Trend Score is kept in the API and is not shown in the detail panel. Direction on screen uses Uptrend and Downtrend wording. The API Trend states are unchanged.

## Intent

The primary question is:

```text
WHAT IS THE STATE OF THE MAJOR MARKETS RIGHT NOW, AND WHAT CHANGED?
```

A finance-aware user answers that from the first view in about two seconds. The user does not calculate, interpret a chart, remember an indicator rule, open seven cards, hover a row, read prose, or inspect a formula. The first view is categorical. Numbers come second.

The screen is dense analytical software in the MEEM visual family. It is not the marketing homepage. It does not contain a large Engineering Intelligence hero, a giant decorative logo, marketing capability cards, or website calls to action. The website defines the brand. The application defines the workspace.

## Authority

Visual decisions follow the order in `MEEM_DESIGN_SYSTEM.md`. The production brand pack wins over an older choice in this document. Market Regime Monitor uses the shared MEEM tokens. It does not invent a private green, red, amber, or information colour. Product-specific state mapping is in this file. The reusable token file stays generic.

## Market State Board

The board is one institutional table. It is not seven oversized cards. It has exactly six columns, in this order, and no seventh primary finance column:

```text
MARKET | DIRECTION | MOMENTUM | VOL | RELATIVE | CHANGE
```

There is no composite regime column, score, confidence, or recommendation.

Stable order. The board is never reordered by performance, direction, volatility, or alerts. Location is part of the scan.

| Order | Market | Ticker |
|---|---|---|
| 1 | S&P 500 | SPY |
| 2 | Nasdaq 100 | QQQ |
| 3 | Russell 2000 | IWM |
| 4 | UK Equities | EWU |
| 5 | Germany Equities | EWG |
| 6 | Japan Equities | EWJ |
| 7 | Emerging Markets | EEM |

ACWI is the benchmark. It is not a board row.

The market cell shows the display name, then the ticker. `display_name` is presentation and configuration data. It is not a field of `MarketRegimeSnapshot`.

```text
S&P 500
SPY
```

Conceptual desktop widths, as guidance only: MARKET 24%, DIRECTION 15%, MOMENTUM 18%, VOL 11%, RELATIVE 22%, CHANGE 10%. A long label does not resize the board.

A row is about 48–54 px. All seven markets fit the primary desktop view. Every row uses the same column order, type, spacing, vocabulary, and interaction. Geography does not change the visual grammar.

Examples:

```text
Nasdaq 100  | STRONG UPTREND | ACCELERATING  | ELEVATED | OUTPERFORM        | M
UK Equities | DOWNTREND      | DETERIORATING | HIGH     | STRONG OUTPERFORM | V
```

The second row is a valid state. A falling market with deteriorating pace and high realised volatility can still be strongly ahead of ACWI.

## State cells

Each cell shows the written category: STRONG UPTREND, ACCELERATING, ELEVATED, OUTPERFORM. Colour reinforces the words. A small line or dot may sit beside the label. Stronger categories use heavier type and a small structural marker. They do not use a different hue.

Direction on screen is Strong Uptrend, Uptrend, Neutral, Downtrend, or Strong Downtrend. Those words present the internal Trend states Strong Up, Up, Neutral, Down, and Strong Down. The API and the colour map keep the internal states. Momentum, Volatility, and Relative Performance are unchanged.

Up and Strong Up share the positive hue. Down and Strong Down share the negative hue. Outperform and Strong Outperform share the positive hue. Colour is never the only difference.

Cells do not use a large bright fill, a traffic light without text, a giant badge, an emoji, or a recommendation arrow. Ordinary labels such as STRONG UPTREND, DOWNTREND, ACCELERATING, DETERIORATING, HIGH, OUTPERFORM, and N/A are readable without a legend.

The scanning row does not show SMA50, SMA200, the 21-session or 63-session returns, pace, RV21, the volatility percentile, active return, or reason codes. The board answers what state. The detail panel answers why.

## Semantic mapping

This mapping is specific to Market Regime Monitor. The colours are the shared tokens in `MEEM_DESIGN_SYSTEM.md`.

Positive:

- Direction: Strong Up, Up
- Momentum: Accelerating, Positive
- Relative Performance: Strong Outperform, Outperform

Negative:

- Direction: Down, Strong Down
- Momentum: Negative, Deteriorating
- Relative Performance: Underperform, Strong Underperform

Neutral:

- Direction: Neutral
- Momentum: Mixed
- Relative Performance: Neutral
- Volatility: Low, Normal

Attention:

- Volatility: Elevated
- Volatility: High, with stronger type and a marker, still the attention hue

Information:

- What Changed dimension letters D, M, V, and R

Unavailable:

- N/A, including insufficient comparison history

System error is only a genuine failed validation, invalid data, a failed operation, or an integrity failure. A negative market state is not coloured as a system error.

Volatility is not a directional judgement. Low and Normal are neutral. Elevated and High are attention. High volatility is not system-error red.

## Change column

What Changed is implemented in the library. The board column and the detail section present it. The column glyphs are presentation only. The finance model does not store these glyphs.

| Status | Cell |
|---|---|
| CHANGED | `D`, `M`, `V`, `R` in that order |
| UNCHANGED | `—` |
| UNAVAILABLE | `N/A` |

Examples of a changed cell: `M`, `D M`, `M V R`, `D M V R`. Changed letters use information styling. Unchanged uses the neutral muted treatment. Unavailable uses unavailable styling. The column does not use green, red, an up arrow, a down arrow, `+1`, `-1`, GOOD, or BAD.

The screen reads `change_status` and `transitions`. It does not recompute them.

## Header

The header is compact. It is not a row of large KPI cards, and it is not the marketing-site navigation.

Left: the official MEEM standalone mark, then MARKET REGIME MONITOR.

Context, as short facts:

```text
AS OF      <date>
BENCHMARK  ACWI
UNIVERSE   7 MARKETS
DATA       VALID
```

DATA VALID appears only when the application has passed the validation layer. It is not a decoration.

Sapphire, through the accessible dark accent where a dark surface requires it, is used sparingly: a thin rule, the selected row, active navigation, a primary action, and a brand separator. The application is not a blue field.

## Selection and eye path

A selected row uses a subtle surface change and a 2 px marker in `dark.accent_accessible`. Keyboard focus is visible. There is no glow. Selection does not change the finance meaning.

The eye path is MARKET, DIRECTION, MOMENTUM, VOL, RELATIVE, CHANGE. Nothing sits between the header and the rows except the column headings. Charts are not placed above the board.

## Detail

Selecting a market opens the evidence. On a wide desktop the detail is a panel to the right and the board stays visible. On a narrower screen the detail may sit beneath the board. The board remains recognisable.

The panel shows the market, `market_id`, and `as_of_date`, then:

- Direction: state, adjusted close, SMA50, SMA200, reason code
- Momentum: state, 21-session return, 63-session return, 21-session pace, 63-session pace, reason code
- Volatility: regime, RV21, historical percentile, below count, equal count, reference size, reason code
- Relative Performance: state, asset return 63, ACWI return 63, active return 63, reason code
- What Changed: status, and every transition as previous state to current state

Every number comes from the existing result objects. The interface performs no finance calculation.

V1 does not add RSI, MACD, stochastic, Bollinger overlays, a candlestick wall, or gauge clusters. Charts are not required to understand the current state. A simple price history may appear in the detail as secondary evidence. It is not the primary interface.

## Layout

Desktop first, from 1366 px. On a wide screen the board and the detail panel may sit together. The analytical working width is about 1400–1600 px. Extra width may hold the detail panel. Rows are not stretched into empty cells on an ultrawide monitor.

On a narrow screen all six finance columns remain. A dimension is not hidden to fit. The board may scroll horizontally inside its own container. The page does not scroll horizontally. A sticky MARKET column may be used later. It is not part of V1.

## Acceptance

The first view is acceptable when a finance-aware user can, in about two seconds, see which markets are Up or Down, which are Accelerating or Deteriorating, where volatility is Elevated or High, which are Outperforming or Underperforming ACWI, and which markets changed state, without opening detail, reading a formula, using a legend, or studying a graph.

Within about five seconds the same user can also pick out the strongest apparent trend category, the elevated or high volatility markets, benchmark underperformance, and whether any state changed. That is a usability objective. It is not a ranking algorithm.

After a market is selected, the user can answer why the board says what it says from the exact numbers, the category, the reason codes, and the What Changed transitions, without the interface recalculating anything.

## Separate ranking

Leaders and laggards are not the board. They are a separate ranking by the continuous `active_return_63` value. An example order is QQQ +6.8 percent, SPY +2.7 percent, EWJ +1.4 percent, and EEM -4.8 percent. The classification label is shown with that value. Ordering does not come from the label alone. ACWI is not ranked. The interface displays the library value and does not recompute it. This ranking does not reorder the Market State Board.

## Freshness and failures

The header shows the as-of date. An asset that failed staleness, history, or another validation check is unavailable, with the library error. It is not shown as Neutral. A failed operation uses system-error styling. A Down or Strong Down state does not.

## Excluded from V1

- a composite score, confidence, or recommendation
- BUY or SELL callouts
- fake gauges, needle motion, and decorative bezels
- AI-written market commentary
- any calculation that is not already in the library output
- a chosen UI framework
