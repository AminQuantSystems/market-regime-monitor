"""JSON shapes for the board endpoint. Fields follow the finance dataclasses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TrendDTO(_Model):
    market_id: str
    as_of_date: str
    adjusted_close: float
    sma_50: float
    sma_200: float
    trend_score: int
    trend_state: str
    reason_code: str


class MomentumDTO(_Model):
    market_id: str
    as_of_date: str
    adjusted_close: float
    return_21: float
    return_63: float
    pace_21: float
    pace_63: float
    momentum_state: str
    reason_code: str


class VolatilityDTO(_Model):
    market_id: str
    as_of_date: str
    adjusted_close: float
    realized_volatility_21: float
    historical_below_count: int
    historical_equal_count: int
    historical_reference_size: int
    historical_percentile: float
    volatility_regime: str
    reason_code: str


class RelativePerformanceDTO(_Model):
    market_id: str
    benchmark_id: str
    as_of_date: str
    adjusted_close: float
    benchmark_adjusted_close: float
    asset_return_63: float
    benchmark_return_63: float
    active_return_63: float
    relative_performance_state: str
    reason_code: str


class CurrentDTO(_Model):
    trend: TrendDTO
    momentum: MomentumDTO
    volatility: VolatilityDTO
    relative_performance: RelativePerformanceDTO


class TransitionDTO(_Model):
    dimension: str
    previous_state: str
    current_state: str


class ChangeDTO(_Model):
    status: str
    reason_code: str
    previous_as_of_date: str | None
    transitions: list[TransitionDTO]


class MarketDTO(_Model):
    market_id: str
    display_name: str
    current: CurrentDTO
    change: ChangeDTO


class BoardResponse(_Model):
    as_of_date: str
    evaluation_date: str
    benchmark_id: str
    universe_size: int
    validation_status: Literal["VALID"]
    data_source: Literal["demo", "upload"]
    data_label: str | None
    markets: list[MarketDTO]


class ErrorBody(_Model):
    code: str
    message: str
    category: str


class ErrorResponse(_Model):
    error: ErrorBody
