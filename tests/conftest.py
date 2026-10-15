import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def panel():
    """Handcrafted numerical fixture, not historical market data."""
    dates = pd.bdate_range("2020-01-01", periods=90)
    close = pd.DataFrame(
        {
            "A": 100 + np.arange(90),
            "B": 200 + np.arange(90) * 0.3,
            "C": 70 + np.sin(np.arange(90) / 5),
        },
        index=dates,
    )
    close = close.astype(float)
    return {
        "open": close * 0.99,
        "high": close * 1.02,
        "low": close * 0.98,
        "close": close,
        "volume": close * 1000,
    }
