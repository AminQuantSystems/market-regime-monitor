# Interface concept

**Status:** concept for owner review. No interface will be built in Phase 0.

## Intent

The interface should feel like a restrained instrument panel: dense, legible, and calm enough to read in a few seconds. The aviation reference is limited to that discipline. V1 is not an aviation theme. No yokes, attitude indicators, altimeter skins, runway graphics, or decorative gauges.

Market Regime Monitor must be visually distinct from Portfolio Risk X-Ray. Portfolio Risk X-Ray uses a blue allocation band and amber concentration marks on a navy field. This product should use a darker charcoal field, a single cool status hue for neutral information, and a separate muted pair for up and down states. Colour encodes state. It is not decoration.

## Primary principle

A user understands the state of the configured markets in approximately 3–5 seconds.

The first screen answers, in order:

1. What is the directional state of each market?
2. Which of trend, momentum, and relative strength support that state, and is volatility calm or elevated?
3. What changed?

## Market State Board

The board is the primary surface. It is a compact set of market cards, one card per configured asset, in a stable order.

Each card shows only:

- asset name
- directional state: Strong Up, Up, Neutral, Down, or Strong Down
- four instrument readings: Trend, Momentum, Volatility, Relative Strength
- a short reason line taken from the library reason code, not composed by the interface
- data freshness for that asset

The directional wording is a state name. The card must not say buy, sell, overweight, or underweight.

Cards are readable without hover text. Nothing required for the 3–5 second reading may depend on a tooltip.

## What changed

A single panel lists state transitions since the approved comparison horizon: asset, instrument or directional state, previous label, new label. If nothing in the approved labels changed, the panel says so. It does not invent a narrative.

## Leaders and laggards

Leaders and laggards are the enabled board markets ordered by the continuous relative-strength value, the 63-day return minus the ACWI 63-day return. The category label is shown with that value. Ordering does not come from the category alone. ACWI is not a normal board card. The interface displays the library value and does not recompute it.

## Freshness

The board shows the as-of date of the calculation and whether any asset failed staleness or history checks. A failed asset is shown as unavailable with the library error. It is not shown as Neutral.

## Drill-down

Selecting a card opens the explanation for that asset:

- each instrument's measurements (for example the two momentum returns, the annualised volatility, the percentile, and the excess return)
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
