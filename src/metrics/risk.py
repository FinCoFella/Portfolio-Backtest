import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def std_dev_annualized(dr: pd.Series) -> float:
    """Annualized standard deviation: daily std dev scaled by sqrt(252)."""
    return dr.std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def max_drawdown(dr: pd.Series) -> float:
    """
    Largest peak-to-trough decline over the period.
    Computed on the cumulative return curve from the daily return series.
    Returns a negative number (e.g. -0.33 means a 33% drawdown).
    """
    cumulative = (1 + dr).cumprod()
    rolling_peak = cumulative.cummax()
    drawdown = (cumulative - rolling_peak) / rolling_peak
    return drawdown.min()


def var(dr: pd.Series, confidence: float = 0.95) -> float:
    """
    Historical daily Value at Risk at the given confidence level.
    Returns a positive number representing the loss threshold.
    e.g. 0.02 means: on (1-confidence)% of days, losses exceeded 2%.
    """
    return float(-np.percentile(dr, (1 - confidence) * 100))


def expected_shortfall(dr: pd.Series, confidence: float = 0.95) -> float:
    """
    Expected Shortfall (ES) at the given confidence level.
    Average loss on the days that fall beyond the VaR threshold.
    Returns a positive number.
    """
    threshold = np.percentile(dr, (1 - confidence) * 100)
    tail = dr[dr <= threshold]
    return float(-tail.mean())


def summary(
    price_data: dict[str, pd.DataFrame], confidence: float = 0.95
) -> pd.DataFrame:
    """
    Compute risk metrics for every ticker in price_data.

    Returns a DataFrame with tickers as rows and metrics as columns:
        std_dev_annualized, max_drawdown, var_daily, es_daily
    """
    from src.metrics.returns import daily_returns

    rows = []
    for ticker, df in price_data.items():
        if len(df) < 2:
            continue
        dr = daily_returns(df)
        rows.append({
            "ticker":             ticker,
            "std_dev_annualized": std_dev_annualized(dr),
            "max_drawdown":       max_drawdown(dr),
            f"var_{int(confidence*100)}_daily": var(dr, confidence),
            f"es_{int(confidence*100)}_daily":  expected_shortfall(dr, confidence),
        })

    return pd.DataFrame(rows).set_index("ticker")
