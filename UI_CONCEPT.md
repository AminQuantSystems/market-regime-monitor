# Interface concept

**Status:** Interface concept. No interface is implemented. Current project status is in `PROJECT_STATE.md`.

## Intent

The interface should feel like a restrained control-room instrument panel: dense, legible, and calm enough to scan. It is not an aviation theme. No decorative gauges are required to read the state.

Market Regime Monitor must be visually distinct from Portfolio Risk X-Ray. Portfolio Risk X-Ray uses a blue allocation band and amber concentration marks on a navy field. This product should use a darker charcoal field, a single cool status hue for neutral information, and a separate muted pair for up and down states. Colour encodes state. It is not decoration, and colour is never the only carrier of meaning.

## Two-second requirement

A user must be able to understand the core state of one market in approximately two seconds. This is a hard requirement for the primary Market State Board.

The board uses fixed columns, in this order:

```text
MARKET | DIRECTION | MOMENTUM | VOL | RELATIVE | CHANGE
```

Direction is the Trend state. It is a heading, not a second calculation. Examples:

```text
NASDAQ 100  | STRONG UP | ACCELERATING  | ELEVATED | OUTPERFORM        | M
UK EQUITIES | DOWN      | DETERIORATING | HIGH     | STRONG OUTPERFORM | V
```

The second row is a valid state. The market can be falling, with deteriorating pace and high realised volatility, and still be strongly ahead of the common ACWI benchmark.

Design rules for that scan:

- Words come before raw numbers.
- Every market uses the same column positions and the same visual grammar.
- Colour is restrained and institutional. A label remains readable without its colour.
- No gauge is required to interpret a state.
- No conventional indicator chart is required to understand the state.
- The user does not calculate anything.
- Ordinary state labels do not need a legend.
- Detailed figures and reason codes appear on drill-down.
- The primary screen is for scanning, not for analytical density.

The four words together are the regime signature, for example Strong Up / Accelerating / Elevated / Outperform. The interface shows that tuple. It does not collapse it into one score, one probability, or a name such as Risk-On or Crisis.

## Market State Board

The board is the primary surface. It is one row per configured asset, in a stable order.

Each row shows:

- market name
- Direction, which is the Trend state: Strong Up, Up, Neutral, Down, or Strong Down
- Momentum: Accelerating, Positive, Mixed, Negative, or Deteriorating
- Volatility: Low, Normal, Elevated, or High
- Relative Performance: Strong Outperform, Outperform, Neutral, Underperform, or Strong Underperform
- a compact change mark, once What Changed exists

The row must not say buy, sell, overweight, or underweight. Nothing required for the two-second reading may depend on a tooltip.

The future row reads the current snapshot and the change result. It does not reformat the approved state labels and it does not calculate them:

- MARKET is the configured `display_name`, joined in presentation from `market_id`
- DIRECTION is `current_snapshot.trend.trend_state`
- MOMENTUM is `current_snapshot.momentum.momentum_state`
- VOL is `current_snapshot.volatility.volatility_regime`
- RELATIVE is `current_snapshot.relative_performance.relative_performance_state`
- CHANGE is the change status plus the changed dimension letters

CHANGE is presentation of a result that does not exist yet. `CHANGED` shows the letters that changed, in order: `D`, `M`, `V`, `R`. Examples are `M`, `D M`, `M V R`, and `D M V R`. `UNCHANGED` shows `—`. `UNAVAILABLE` shows `N/A`. The primary column does not use an arrow. An arrow would imply better or worse, and V1 does not make that judgement. Drill-down shows the words, such as Momentum Positive to Accelerating, and may say `No market-state change since previous session` only for `UNCHANGED`.

## What changed

What Changed is designed and is not implemented. A transition is a change in Direction, Momentum, Volatility, or Relative Performance. There is no composite-regime transition. The comparison retains every changed dimension. It does not keep only one of them. The finance result stores the two snapshots and the transition labels. It does not store colours or the compact `D` `M` `V` `R` strings.

## Shared MEEM visual system

Every MEEM finance and investment-technology product uses one visual system taken from the MEEM Technologies website. Market Regime Monitor is the first project that will define reusable MEEM design tokens, and that work waits for the UI phase. The website palette is inspected before any token is final. This concept does not set colour values.

The shared system requires one base brand palette, the same colour for the same meaning in every tool, and shared background, surface, accent, border, typography, spacing, and control conventions. Styling stays restrained and institutional. It does not use a retail-trading red and green overload. Colour is never the only carrier of meaning: the text, state label, or symbol remains sufficient. Accessibility and legibility are mandatory. The two-second reading outranks decoration.

What Changed logic contains no colour. A later screen may highlight a changed `D`, `M`, `V`, or `R` marker with those shared semantic tokens. The change model itself knows only the dimension and the two state labels.

## Leaders and laggards

Leaders and laggards are a separate ranking, not the five Benchmark Relative Performance labels. The panel orders enabled board markets by the continuous `active_return_63` value, the asset's 63-observation return minus the return of the common ACWI comparison benchmark. An example order is QQQ +6.8 percent, SPY +2.7 percent, EWJ +1.4 percent, and EEM -4.8 percent. The classification label, such as Strong Outperform or Underperform, is shown with that value. Ordering does not come from the label alone. ACWI is not ranked. The interface displays the library value and does not recompute it.

## Freshness

The board shows the as-of date of the calculation and whether any asset failed staleness or history checks. A failed asset is shown as unavailable with the library error. It is not shown as Neutral.

## Drill-down

Selecting a card opens the explanation for that asset:

- each instrument's measurements (for example the two momentum returns, the annualised volatility, the percentile, and the 63-observation active return)
- the rule that fired
- the reason code
- the prior label used by "What changed"

This is the audit view. It is not a second dashboard.

## Charts

A simple price history may appear in the drill-down as secondary evidence. It is not the primary interface. V1 does not draw a chart overlaid with moving-average lines, momentum oscillators, and volatility bands.

## Explicitly excluded

- fake gauges and needle animations
- decorative instrument bezels
- unexplained risk scores or confidence meters
- AI-written market commentary
- BUY/SELL callouts
- any calculation not already present in the library output

## Presentation rules

- Dark, high-contrast, and quiet.
- One question per region.
- User-supplied names, if any are ever rendered into custom markup, are escaped.
- The interface remains usable if JavaScript charting is absent, because the board does not depend on a chart.
