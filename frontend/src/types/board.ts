export type TrendState = "Strong Up" | "Up" | "Neutral" | "Down" | "Strong Down"
export type MomentumState = "Accelerating" | "Positive" | "Mixed" | "Negative" | "Deteriorating"
export type VolatilityRegime = "Low" | "Normal" | "Elevated" | "High"
export type RelativePerformanceState =
  | "Strong Outperform"
  | "Outperform"
  | "Neutral"
  | "Underperform"
  | "Strong Underperform"
export type ChangeStatus = "CHANGED" | "UNCHANGED" | "UNAVAILABLE"
export type ChangeDimension = "direction" | "momentum" | "volatility" | "relative_performance"

export interface TrendReading {
  market_id: string
  as_of_date: string
  adjusted_close: number
  sma_50: number
  sma_200: number
  trend_score: number
  trend_state: TrendState
  reason_code: string
}

export interface MomentumReading {
  market_id: string
  as_of_date: string
  adjusted_close: number
  return_21: number
  return_63: number
  pace_21: number
  pace_63: number
  momentum_state: MomentumState
  reason_code: string
}

export interface VolatilityReading {
  market_id: string
  as_of_date: string
  adjusted_close: number
  realized_volatility_21: number
  historical_below_count: number
  historical_equal_count: number
  historical_reference_size: number
  historical_percentile: number
  volatility_regime: VolatilityRegime
  reason_code: string
}

export interface RelativePerformanceReading {
  market_id: string
  benchmark_id: string
  as_of_date: string
  adjusted_close: number
  benchmark_adjusted_close: number
  asset_return_63: number
  benchmark_return_63: number
  active_return_63: number
  relative_performance_state: RelativePerformanceState
  reason_code: string
}

export interface StateTransition {
  dimension: ChangeDimension
  previous_state: string
  current_state: string
}

export interface ChangeReading {
  status: ChangeStatus
  reason_code: string
  previous_as_of_date: string | null
  transitions: StateTransition[]
}

export interface MarketReading {
  market_id: string
  display_name: string
  current: {
    trend: TrendReading
    momentum: MomentumReading
    volatility: VolatilityReading
    relative_performance: RelativePerformanceReading
  }
  change: ChangeReading
}

export interface BoardResponse {
  as_of_date: string
  evaluation_date: string
  benchmark_id: string
  universe_size: number
  validation_status: "VALID"
  data_source: "demo" | "upload"
  data_label: string | null
  markets: MarketReading[]
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    category: string
  }
}
