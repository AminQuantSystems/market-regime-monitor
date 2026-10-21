import type {
  ChangeStatus,
  MomentumState,
  RelativePerformanceState,
  TrendState,
  VolatilityRegime,
} from "../types/board"

export type SemanticToken = "positive" | "negative" | "attention" | "neutral" | "information" | "unavailable"
export type Emphasis = "base" | "strong"

export interface Presentation {
  semantic: SemanticToken
  emphasis: Emphasis
}

const trend: Record<TrendState, Presentation> = {
  "Strong Up": { semantic: "positive", emphasis: "strong" },
  Up: { semantic: "positive", emphasis: "base" },
  Neutral: { semantic: "neutral", emphasis: "base" },
  Down: { semantic: "negative", emphasis: "base" },
  "Strong Down": { semantic: "negative", emphasis: "strong" },
}

const momentum: Record<MomentumState, Presentation> = {
  Accelerating: { semantic: "positive", emphasis: "base" },
  Positive: { semantic: "positive", emphasis: "base" },
  Mixed: { semantic: "neutral", emphasis: "base" },
  Negative: { semantic: "negative", emphasis: "base" },
  Deteriorating: { semantic: "negative", emphasis: "base" },
}

const volatility: Record<VolatilityRegime, Presentation> = {
  Low: { semantic: "neutral", emphasis: "base" },
  Normal: { semantic: "neutral", emphasis: "base" },
  Elevated: { semantic: "attention", emphasis: "base" },
  High: { semantic: "attention", emphasis: "strong" },
}

const relative: Record<RelativePerformanceState, Presentation> = {
  "Strong Outperform": { semantic: "positive", emphasis: "strong" },
  Outperform: { semantic: "positive", emphasis: "base" },
  Neutral: { semantic: "neutral", emphasis: "base" },
  Underperform: { semantic: "negative", emphasis: "base" },
  "Strong Underperform": { semantic: "negative", emphasis: "strong" },
}

const change: Record<ChangeStatus, Presentation> = {
  CHANGED: { semantic: "information", emphasis: "base" },
  UNCHANGED: { semantic: "neutral", emphasis: "base" },
  UNAVAILABLE: { semantic: "unavailable", emphasis: "base" },
}

export function presentTrend(state: TrendState): Presentation {
  return trend[state]
}

export function presentMomentum(state: MomentumState): Presentation {
  return momentum[state]
}

export function presentVolatility(state: VolatilityRegime): Presentation {
  return volatility[state]
}

export function presentRelative(state: RelativePerformanceState): Presentation {
  return relative[state]
}

export function presentChange(status: ChangeStatus): Presentation {
  return change[status]
}
