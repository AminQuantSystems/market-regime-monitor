"""Approved V1 market configuration.

Display names are application metadata. They are not fields of MarketRegimeSnapshot.
"""

from __future__ import annotations

import pandas as pd

V1_MARKETS = (
    ("SPY", "S&P 500", True),
    ("QQQ", "Nasdaq 100", True),
    ("IWM", "Russell 2000", True),
    ("EWU", "UK Equities", True),
    ("EWG", "Germany Equities", True),
    ("EWJ", "Japan Equities", True),
    ("EEM", "Emerging Markets", True),
    ("ACWI", "ACWI", False),
)


def v1_configuration() -> pd.DataFrame:
    """Return the approved configuration for validate_configuration."""
    return pd.DataFrame(
        [
            {
                "market_id": market_id,
                "display_name": display_name,
                "benchmark_id": "ACWI",
                "enabled": enabled,
            }
            for market_id, display_name, enabled in V1_MARKETS
        ]
    )
