"""Market State Flight Deck.

Phase 1A validates local prices and market configuration.
Indicator calculations are not part of this package yet.
"""

from market_state.errors import MarketDataError
from market_state.validation import validate_configuration, validate_market_data

__all__ = [
    "MarketDataError",
    "validate_configuration",
    "validate_market_data",
]
