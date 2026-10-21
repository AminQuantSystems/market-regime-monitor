import type { BoardResponse, ChangeReading, MarketReading } from "../types/board"

const SENTINEL = {
  sma50: 111111.111,
  sma200: 111112.111,
  return21: 222222.222,
  return63: 222223.222,
  pace21: 666666.666,
  pace63: 666667.666,
  rv21: 333333.333,
  percentile: 444444.444,
  active: 555555.555,
  reason: "REASON_SHOULD_NOT_RENDER",
}

function market(
  marketId: string,
  displayName: string,
  trend: MarketReading["current"]["trend"]["trend_state"],
  momentum: MarketReading["current"]["momentum"]["momentum_state"],
  volatility: MarketReading["current"]["volatility"]["volatility_regime"],
  relative: MarketReading["current"]["relative_performance"]["relative_performance_state"],
  change: ChangeReading,
): MarketReading {
  return {
    market_id: marketId,
    display_name: displayName,
    current: {
      trend: {
        market_id: marketId,
        as_of_date: "2026-03-01",
        adjusted_close: 101.5,
        sma_50: SENTINEL.sma50,
        sma_200: SENTINEL.sma200,
        trend_score: 2,
        trend_state: trend,
        reason_code: SENTINEL.reason,
      },
      momentum: {
        market_id: marketId,
        as_of_date: "2026-03-01",
        adjusted_close: 101.5,
        return_21: SENTINEL.return21,
        return_63: SENTINEL.return63,
        pace_21: SENTINEL.pace21,
        pace_63: SENTINEL.pace63,
        momentum_state: momentum,
        reason_code: SENTINEL.reason,
      },
      volatility: {
        market_id: marketId,
        as_of_date: "2026-03-01",
        adjusted_close: 101.5,
        realized_volatility_21: SENTINEL.rv21,
        historical_below_count: 200,
        historical_equal_count: 0,
        historical_reference_size: 252,
        historical_percentile: SENTINEL.percentile,
        volatility_regime: volatility,
        reason_code: SENTINEL.reason,
      },
      relative_performance: {
        market_id: marketId,
        benchmark_id: "ACWI",
        as_of_date: "2026-03-01",
        adjusted_close: 101.5,
        benchmark_adjusted_close: 100.2,
        asset_return_63: 0.04,
        benchmark_return_63: 0.01,
        active_return_63: SENTINEL.active,
        relative_performance_state: relative,
        reason_code: SENTINEL.reason,
      },
    },
    change,
  }
}

export const boardFixture: BoardResponse = {
  as_of_date: "2026-03-01",
  evaluation_date: "2026-03-01",
  benchmark_id: "ACWI",
  universe_size: 7,
  validation_status: "VALID",
  data_source: "demo",
  data_label: "DEMO DATA",
  markets: [
    market("SPY", "S&P 500", "Strong Up", "Positive", "Low", "Outperform", {
      status: "UNCHANGED",
      reason_code: "CHANGE_NO_STATE_CHANGE",
      previous_as_of_date: "2026-02-28",
      transitions: [],
    }),
    market("QQQ", "Nasdaq 100", "Strong Up", "Accelerating", "Elevated", "Outperform", {
      status: "CHANGED",
      reason_code: "CHANGE_STATE_CHANGED",
      previous_as_of_date: "2026-02-28",
      transitions: [{ dimension: "momentum", previous_state: "Positive", current_state: "Accelerating" }],
    }),
    market("IWM", "Russell 2000", "Strong Down", "Deteriorating", "High", "Strong Underperform", {
      status: "UNCHANGED",
      reason_code: "CHANGE_NO_STATE_CHANGE",
      previous_as_of_date: "2026-02-28",
      transitions: [],
    }),
    market("EWU", "UK Equities", "Up", "Mixed", "Low", "Neutral", {
      status: "UNCHANGED",
      reason_code: "CHANGE_NO_STATE_CHANGE",
      previous_as_of_date: "2026-02-28",
      transitions: [],
    }),
    market("EWG", "Germany Equities", "Down", "Negative", "Normal", "Underperform", {
      status: "UNAVAILABLE",
      reason_code: "CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY",
      previous_as_of_date: null,
      transitions: [],
    }),
    market("EWJ", "Japan Equities", "Neutral", "Mixed", "Normal", "Neutral", {
      status: "UNCHANGED",
      reason_code: "CHANGE_NO_STATE_CHANGE",
      previous_as_of_date: "2026-02-28",
      transitions: [],
    }),
    market("EEM", "Emerging Markets", "Strong Down", "Deteriorating", "High", "Strong Underperform", {
      status: "CHANGED",
      reason_code: "CHANGE_STATE_CHANGED",
      previous_as_of_date: "2026-02-28",
      transitions: [
        { dimension: "direction", previous_state: "Down", current_state: "Strong Down" },
        { dimension: "momentum", previous_state: "Mixed", current_state: "Deteriorating" },
        { dimension: "volatility", previous_state: "Low", current_state: "High" },
        { dimension: "relative_performance", previous_state: "Underperform", current_state: "Strong Underperform" },
      ],
    }),
  ],
}

export const hiddenMeasurements = [
  "111111.111",
  "222222.222",
  "333333.333",
  "444444.444",
  "555555.555",
  "666666.666",
  "REASON_SHOULD_NOT_RENDER",
]
