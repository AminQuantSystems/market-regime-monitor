# UI architecture

**Status:** approved architecture. Not implemented.
**Phase:** 2B
**Finance core:** `src/market_state/` remains the authority and stays frozen for V1 UI work.
**Visual system:** `MEEM_DESIGN_SYSTEM.md` and `MEEM_DESIGN_TOKENS.json`.
**Screen specification:** `UI_CONCEPT.md`.

This document chooses the V1 application shape. It does not add dependencies, routes, or a screen.

## Technology

```text
React + TypeScript + Vite
        |
        v
HTTP / JSON
        |
        v
FastAPI adapter
        |
        v
existing Python market_state package
```

Python remains the finance authority. The frontend does not reimplement Trend, Momentum, Volatility, Relative Performance, `MarketRegimeSnapshot`, or What Changed.

React and TypeScript are the V1 frontend because the product needs precise fidelity to the MEEM design system, a dense institutional board, keyboard use, responsive layout, a drill-down panel, reusable components, shared design tokens, direct accessibility control, and a public portfolio surface that can be shared by later MEEM tools. The screen should look like bespoke MEEM analytical software.

Streamlit remains a sound choice for rapid research tools, internal prototypes, small Python analytics utilities, and exploratory dashboards. It is not the V1 implementation for Market Regime Monitor. This product now has an authoritative corporate design system, exact density, interaction and accessibility requirements, reusable tokens, and a public portfolio position. Streamlit is not added.

Vite is the frontend toolchain. Market Regime Monitor V1 is an analytical application. It does not need search-engine rendering, server-side rendering, content pages, server components, or a website router. Next.js is not used. The architecture stays small and does not take on a framework feature because the framework offers it.

FastAPI is a thin adapter. It parses the HTTP request, checks the file and request boundary, calls the existing Python functions, maps immutable result objects to JSON, and translates known project errors into HTTP responses. It does not own formulas, thresholds, state logic, change calculations, or new market rules. Finance logic is not copied into routes or into Pydantic models.

## Repository shape

The repository today is a `src` layout: `src/market_state/` is the importable finance package, `tests/` holds the finance tests, and `pyproject.toml` discovers packages only under `src`. There is no application package and no frontend.

The smallest addition that respects that layout:

```text
src/market_state/          finance core, unchanged
tests/                     existing finance tests
app/api/                   FastAPI adapter
    main.py
    routes/
    schemas.py
    mapping.py
    errors.py
frontend/                  React application
    src/app/
    src/components/
    src/features/
    src/design-system/
    src/api/
    src/types/
    public/
```

`app` is not added to the `market_state` package. The frontend does not live inside `src/market_state/`. One Python process and one web frontend are the whole V1 deployment unit. Trend, Momentum, Volatility, and Relative Performance are modules in one library. They are not network services.

## Board endpoint

```text
POST /api/v1/market-regime/analyse
```

The body is `multipart/form-data`.

| Field | Required | Meaning |
|---|---|---|
| `prices` | when `data_source` is `upload` | CSV file. Columns are exactly `date`, `market_id`, `adjusted_close`. |
| `evaluation_date` | always | `YYYY-MM-DD`. Passed to `validate_market_data`. This is the freshness gate. It is not read from a clock. |
| `as_of_date` | always | `YYYY-MM-DD`. Passed to `calculate_market_regime_change`. It must be an observation the finance core accepts. |
| `data_source` | always | `upload` or `demo`. |

These two dates stay separate because the finance core already treats them as different inputs. `evaluation_date` decides whether the latest complete observation is future or stale. `as_of_date` selects the observation to calculate. The adapter does not collapse one into the other.

The approved V1 configuration is supplied by the adapter and passed through `validate_configuration`. It is the existing contract: `market_id`, `display_name`, `benchmark_id`, `enabled`, with SPY, QQQ, IWM, EWU, EWG, EWJ, and EEM enabled, and ACWI present, disabled, and named as `benchmark_id`. The price file does not define the universe. The adapter does not invent a path that skips configuration validation.

There is no live feed, no database, and no authentication on this route.

## Request flow

1. Reject a missing file, an oversized body, or an unsupported media type before any finance call.
2. Read the CSV so `date` and `market_id` stay text and `adjusted_close` is not filled, trimmed, interpolated, or rewritten. Invalid cells remain visible to the existing validator. A parser must not uppercase identifiers or drop future rows.
3. Call `validate_configuration` on the approved V1 configuration.
4. Call `validate_market_data` once, with that configuration and `evaluation_date`.
5. Use the requested `as_of_date` as given.
6. For each enabled board market, in fixed order, call `calculate_market_regime_change(prices, market_id, "ACWI", as_of_date)`. The order is SPY, QQQ, IWM, EWU, EWG, EWJ, EEM.
7. Leave ACWI as the benchmark. It is not a board row.
8. Join `display_name` from the validated configuration onto each market.
9. Map the result objects to the response below and return JSON.

Full-panel validation runs once. The selected-market functions are not changed and are not asked to validate the panel again.

A successful response exists only after validation has passed. `validation_status` is `VALID` on that response. A failed validation is an error response, not a board of empty or `N/A` rows.

## Response

Top level:

```json
{
  "as_of_date": "2026-03-09",
  "evaluation_date": "2026-03-09",
  "benchmark_id": "ACWI",
  "universe_size": 7,
  "validation_status": "VALID",
  "data_source": "demo",
  "markets": []
}
```

`as_of_date` and `evaluation_date` are the request values echoed after success. `benchmark_id` is `ACWI`. `universe_size` is the number of market objects, which is 7 for the approved configuration. `data_source` tells the screen whether to show the demo label.

Each market follows the Python objects. Names match the dataclass fields. `realized_volatility_21` keeps the spelling used in `VolatilityResult`.

```json
{
  "market_id": "SPY",
  "display_name": "S&P 500",
  "current": {
    "trend": {
      "market_id": "SPY",
      "as_of_date": "2026-03-09",
      "adjusted_close": 0.0,
      "sma_50": 0.0,
      "sma_200": 0.0,
      "trend_score": 2,
      "trend_state": "Strong Up",
      "reason_code": "TREND_STRONG_UP_ALIGNMENT"
    },
    "momentum": {
      "market_id": "SPY",
      "as_of_date": "2026-03-09",
      "adjusted_close": 0.0,
      "return_21": 0.0,
      "return_63": 0.0,
      "pace_21": 0.0,
      "pace_63": 0.0,
      "momentum_state": "Accelerating",
      "reason_code": "MOMENTUM_ACCELERATING"
    },
    "volatility": {
      "market_id": "SPY",
      "as_of_date": "2026-03-09",
      "adjusted_close": 0.0,
      "realized_volatility_21": 0.0,
      "historical_below_count": 0,
      "historical_equal_count": 0,
      "historical_reference_size": 252,
      "historical_percentile": 0.0,
      "volatility_regime": "Normal",
      "reason_code": "VOLATILITY_NORMAL"
    },
    "relative_performance": {
      "market_id": "SPY",
      "benchmark_id": "ACWI",
      "as_of_date": "2026-03-09",
      "adjusted_close": 0.0,
      "benchmark_adjusted_close": 0.0,
      "asset_return_63": 0.0,
      "benchmark_return_63": 0.0,
      "active_return_63": 0.0,
      "relative_performance_state": "Neutral",
      "reason_code": "RELATIVE_PERFORMANCE_NEUTRAL"
    }
  },
  "change": {
    "status": "UNCHANGED",
    "reason_code": "CHANGE_NO_STATE_CHANGE",
    "previous_as_of_date": "2026-03-06",
    "transitions": []
  }
}
```

The numeric examples above are shape only. A real response carries the full-precision Python values. The adapter does not round them.

`trend_score` is the existing Trend alignment integer on `TrendResult`: 2, 1, 0, -1, or -2. It is included so the JSON still matches that object. It is not a composite regime score, and the board does not render it as a column.

`display_name` is joined from configuration. It is not a field of `MarketRegimeSnapshot`. Finance identity remains `market_id`.

`change.status` is `CHANGED`, `UNCHANGED`, or `UNAVAILABLE`. `previous_as_of_date` is null when the status is `UNAVAILABLE`. A transition is `{ "dimension", "previous_state", "current_state" }`. `dimension` is `direction`, `momentum`, `volatility`, or `relative_performance`, in that order. The Python `previous_snapshot` is not copied into this V1 board document. The detail view reads the current measurements and the transition labels. The adapter still calculates through `calculate_market_regime_change`, which holds that snapshot on the Python object.

Closed labels, copied from the finance core:

| Field | Values |
|---|---|
| `trend_state` | `Strong Up`, `Up`, `Neutral`, `Down`, `Strong Down` |
| `momentum_state` | `Accelerating`, `Positive`, `Mixed`, `Negative`, `Deteriorating` |
| `volatility_regime` | `Low`, `Normal`, `Elevated`, `High` |
| `relative_performance_state` | `Strong Outperform`, `Outperform`, `Neutral`, `Underperform`, `Strong Underperform` |
| `change.status` | `CHANGED`, `UNCHANGED`, `UNAVAILABLE` |

The API returns no colour, no `D`/`M`/`V`/`R` glyph, and no display percentage.

## Errors

```json
{
  "error": {
    "code": "DATA_INVALID_PRICE",
    "message": "adjusted_close is not finite for SPY on 2026-03-09",
    "category": "market_data"
  }
}
```

`code` is the existing project code. `message` is `str(error)` from that exception. The response does not include a traceback, a file path, or a stack frame.

| Condition | HTTP | `category` |
|---|---|---|
| Missing file, unreadable body, or a date field that is not `YYYY-MM-DD` at the HTTP boundary | 400 | `request` |
| Body over the later size limit | 413 | `request` |
| Unsupported media type | 415 | `request` |
| `MarketDataError`, including every `CONFIG_*` and `DATA_*` code | 422 | `market_data` |
| `MarketRegimeError` (`REGIME_COMPONENT_MISMATCH`, `CHANGE_SNAPSHOT_MISMATCH`) | 500 | `regime` |
| Any other exception | 500 | `unexpected`, code `API_UNEXPECTED`, generic message |

Request-boundary codes are adapter codes: `API_MISSING_FILE`, `API_UNSUPPORTED_MEDIA`, `API_PAYLOAD_TOO_LARGE`, `API_INVALID_DATE`. They are not finance codes. A known project error keeps its own code. Failures are not all folded into `400 Bad Request`.

`MarketRegimeError` is an integrity failure after the finance functions have run. The client cannot repair it by editing a cell, so it is 500 with the stable code and no traceback. `MarketDataError` from a calculator, including `DATA_INVALID_DATE` when `as_of_date` is absent, stays 422.

`UNAVAILABLE` is a successful What Changed result. It is not this error document. A validation failure is not rendered as an `N/A` market row.

## Frontend finance boundary

React may render labels, map a label to a semantic token, format a number the API already returned, format a percentage for display, render reason codes and transitions, and hold selection and layout. A return of `0.031245` may be shown as `3.12%`. A percentile of `82.738` may be shown as `82.7`. The formatted string is not written back and is not classified again.

React may not calculate SMA50, SMA200, a 21-session or 63-session return, momentum pace, RV21, a percentile, or an active return. It may not classify a state or decide that a categorical change occurred. If Python did not send a value, the screen does not invent one.

A separate leaders view may order the seven returned `active_return_63` values for display. That ordering uses the returned numbers. It does not recompute them, and it does not reorder the Market State Board.

## Tokens and styling

`MEEM_DESIGN_TOKENS.json` is the only palette authority. A later build step may emit CSS custom properties and a thin TypeScript module of token names from that file. Components refer to those names. Hex values are not copied into a second React palette, and they are not returned by Python.

The starting UI technology is React, TypeScript, and plain CSS with CSS Modules. Material UI, Ant Design, Bootstrap, Chakra, Mantine, Tailwind, shadcn, and styled-components are not assumed. A component kit would bring its own density, radius, colour, and focus language, and the MEEM system is deliberately a 2–4 px institutional surface. CSS Modules give local scope without that kit. The cost is writing a small set of rules by hand. That cost is accepted for V1. A library can be reconsidered only if a later requirement cannot be met in plain CSS.

Icons stay minimal: text labels, the official MEEM standalone mark, and a few inline SVGs if a control needs a non-text cue. An icon package is not justified for this board.

State colours are a frontend map from the categorical strings onto the semantic token names in `MEEM_DESIGN_TOKENS.json`. Strong Up and Up use positive. Down and Strong Down use negative. Elevated and High use attention. The What Changed letters use information. `N/A` uses unavailable. The map stores token names, not hex, and it does not live beside the finance results.

## Components and data flow

```text
API JSON
    -> typed board model
    -> MarketStateBoard
         -> MarketStateHeader
         -> MarketStateRow
              -> StateCell
              -> ChangeCell
    -> selected market id (UI state only)
    -> MarketDetailPanel
         -> InstrumentDetailSection
         -> ChangeDetailSection
```

`AppShell` holds the header, the board, and the panel. `ApplicationHeader` carries the mark, the product title, the as-of date, the benchmark, the universe count, and the validation fact. `ValidationErrorState` replaces the board when the request failed. `LoadingState` is the single status line `ANALYSING MARKET STATE…` in a polite live region. Local calculation has been measured in fractions of a second, so the screen does not use a fake percentage, a full-screen spinner, or a skeleton on every cell. Those timings are diagnostic, not a guarantee.

Selection is frontend state. The finance payload is immutable.

The board is a native HTML table. The six columns are a real row and column relationship, and a table expresses that without an ARIA grid. The market name is a button inside the row. That button selects the market, takes keyboard focus, and is reachable with Tab and the arrow keys between the seven buttons. `aria-selected` records the selected row. Focus is visible. Nothing required to read a state depends on hover.

The detail is a section beside the table on a wide screen and after it on a narrow screen. It has a heading that names the selected market, `aria-labelledby` on the section, and `aria-controls` from the selected button to that section. Transitions are text. It is not a hover card and not a modal.

Reduced motion follows the design system. Contrast and non-colour meaning follow `MEEM_DESIGN_SYSTEM.md` and `UI_CONCEPT.md`.

## TypeScript and drift

Frontend types mirror the response. State fields are unions of the closed labels above. `any` is not the contract.

Pydantic response models are the HTTP contract. FastAPI publishes their OpenAPI schema. The approved later step is to generate the TypeScript types from that schema and to check the generated file in, so the browser types are derived from the adapter models rather than typed again by hand. A hand-maintained duplicate is the drift this avoids. The generator is not installed in this phase.

Generation does not prove that a float or a label still means what the finance core produced. A contract test does. One existing deterministic fixture is run through `calculate_market_regime_change`, mapped by the adapter, and asserted equal in state labels, full-precision numbers, reason codes, transitions, `benchmark_id`, and both dates. The test fails if the adapter rounds, renames a finance field, or drops a transition.

## Input workflow

V1 has no live or vendor data. The approved input is both a bundled demonstration file and a user CSV.

The demonstration opens immediately so the board can be reviewed without hunting for a file. It is labelled `DEMO DATA` on the header whenever `data_source` is `demo`. Its as-of date and evaluation date are the explicit dates stored with that file. The screen does not call them today, live, or real time.

The same endpoint accepts an uploaded CSV so the strict contract can be exercised. The browser checks that a file was selected, that it is within a size limit, and that the name ends in `.csv`. It does not clean, fill, or rewrite the contents. Python validation remains authoritative. A failed upload shows the human-readable message and the stable code, with the corrective context of that code. `DATA_DATE_INDEX_MISMATCH` is a failed request. It is not a set of unavailable market rows. Data unavailable (`N/A` on What Changed after a valid panel) stays distinct from a data or system failure.

## Tests to add later

The current 309 finance tests stay the finance authority. This phase adds none.

Later backend tests cover DTO mapping, error status and code mapping, the one-panel-validation board flow, and the golden fixture contract above.

Later component tests cover semantic token mapping, `ChangeCell` letters in `D` `M` `V` `R` order, the six columns, the fixed market order, detail values taken from the typed model, the error state, and keyboard selection.

An integration test renders the board from an API fixture. An end-to-end pass loads the demo, selects a market, reads the detail, uploads a valid CSV, uploads an invalid CSV, and moves through the rows with the keyboard.

Design-system checks later confirm that CSS colours used for meaning come from the MEEM tokens, that every approved state has a semantic mapping, and that no state is left unmapped. Pixel screenshots of every cell are not the plan. A later visual check of the board and the detail panel is enough if one is added.

## Local run

From the repository root, with the finance package and the `ui` extra installed:

```text
.venv\Scripts\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

From `frontend/`, with Node.js available:

```text
npm run dev
```

Vite serves the board at `http://127.0.0.1:5173` and proxies `/api` to the FastAPI process. The screen loads the bundled demonstration panel for `2026-03-06`. Those dates are fixed weekdays. They are not taken from the clock.

`npm test`, `npm run typecheck`, and `npm run build` regenerate `frontend/src/design-system/tokens.generated.css` from `MEEM_DESIGN_TOKENS.json` before they run. The generated file is not a second palette.

## Local development and build

Two processes, with no Docker requirement and no extra orchestrator:

- one terminal runs FastAPI locally
- one terminal runs the Vite development server
- Vite proxies `/api` to that FastAPI process

The frontend build is a static asset directory. FastAPI may serve those files later, or they may be hosted separately. Either remains possible. CORS is explicit once the processes are split, and it allows only the development and deployment origins that are actually used.

A later simple deployment can be the static build plus the FastAPI application in one container. Cloud vendor, Kubernetes, and extra services are not selected.

## Security baseline

When the adapter is built: limit upload size, check the content rather than trusting the file name, and do not evaluate uploaded content as code. Keep credentials out of source. Return no stack trace to the client. Set an explicit CORS list. Expose only the routes the screen uses. This is the baseline. It is not a security product of its own.

## Performance

The measured local cost, recorded in `PROJECT_STATE.md`, is about 0.22 seconds for seven snapshots and about 0.32 seconds for seven What Changed calculations. Those figures are not guarantees. The current board does not justify WebSockets, a worker queue, Celery, Redis, multiprocessing, or Mac offload. One HTTP request and one JSON response are sufficient.

Mac integration remains unauthorised. This UI workload is not a reason to benchmark the Mac.

## Deferred finding

The pure snapshot comparator still does not re-check malformed nested component identity on a manually constructed snapshot. Production snapshots continue to come from the integrity-hardened snapshot API. This remains deferred low-priority public-API hardening. It is not part of Phase 2B, and `change.py` is not modified.

## Non-goals

- Implementing the UI, the adapter, or the tests described here
- Installing FastAPI, React, Vite, a CSS framework, an icon pack, or a type generator
- Rewriting the finance engine in TypeScript
- Changing formulas, thresholds, classifications, snapshot behaviour, or What Changed behaviour
- Live or vendor data, a database, authentication, or microservices
- A composite score, a recommendation, or colour inside the Python response
- Choosing a cloud vendor or a container platform
- Publishing the repository, opening a remote, or using the Mac
