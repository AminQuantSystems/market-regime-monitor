"""Copy finance result objects into response models. No calculation and no rounding."""

from __future__ import annotations

from market_state.change import MarketRegimeChange

from app.api.schemas import (
    ChangeDTO,
    CurrentDTO,
    MarketDTO,
    MomentumDTO,
    RelativePerformanceDTO,
    TransitionDTO,
    TrendDTO,
    VolatilityDTO,
)


def market_dto(change: MarketRegimeChange, display_name: str) -> MarketDTO:
    snapshot = change.current_snapshot
    trend = snapshot.trend
    momentum = snapshot.momentum
    volatility = snapshot.volatility
    relative = snapshot.relative_performance
    return MarketDTO(
        market_id=change.market_id,
        display_name=display_name,
        current=CurrentDTO(
            trend=TrendDTO(
                market_id=trend.market_id,
                as_of_date=trend.as_of_date,
                adjusted_close=trend.adjusted_close,
                sma_50=trend.sma_50,
                sma_200=trend.sma_200,
                trend_score=trend.trend_score,
                trend_state=trend.trend_state,
                reason_code=trend.reason_code,
            ),
            momentum=MomentumDTO(
                market_id=momentum.market_id,
                as_of_date=momentum.as_of_date,
                adjusted_close=momentum.adjusted_close,
                return_21=momentum.return_21,
                return_63=momentum.return_63,
                pace_21=momentum.pace_21,
                pace_63=momentum.pace_63,
                momentum_state=momentum.momentum_state,
                reason_code=momentum.reason_code,
            ),
            volatility=VolatilityDTO(
                market_id=volatility.market_id,
                as_of_date=volatility.as_of_date,
                adjusted_close=volatility.adjusted_close,
                realized_volatility_21=volatility.realized_volatility_21,
                historical_below_count=volatility.historical_below_count,
                historical_equal_count=volatility.historical_equal_count,
                historical_reference_size=volatility.historical_reference_size,
                historical_percentile=volatility.historical_percentile,
                volatility_regime=volatility.volatility_regime,
                reason_code=volatility.reason_code,
            ),
            relative_performance=RelativePerformanceDTO(
                market_id=relative.market_id,
                benchmark_id=relative.benchmark_id,
                as_of_date=relative.as_of_date,
                adjusted_close=relative.adjusted_close,
                benchmark_adjusted_close=relative.benchmark_adjusted_close,
                asset_return_63=relative.asset_return_63,
                benchmark_return_63=relative.benchmark_return_63,
                active_return_63=relative.active_return_63,
                relative_performance_state=relative.relative_performance_state,
                reason_code=relative.reason_code,
            ),
        ),
        change=ChangeDTO(
            status=change.change_status,
            reason_code=change.reason_code,
            previous_as_of_date=change.previous_as_of_date,
            transitions=[
                TransitionDTO(
                    dimension=transition.dimension,
                    previous_state=transition.previous_state,
                    current_state=transition.current_state,
                )
                for transition in change.transitions
            ],
        ),
    )
