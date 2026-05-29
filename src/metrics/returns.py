import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def daily_returns(df: pd.DataFrame) -> pd.Series:
    """Percentage change in adj_close, day over day. First row is dropped (NaN)."""
    return df["adj_close"].pct_change().dropna()


def total_return(df: pd.DataFrame) -> float:
    """Total return over the full period using first and last adj_close."""
    return (df["adj_close"].iloc[-1] / df["adj_close"].iloc[0]) - 1


def cagr(df: pd.DataFrame) -> float:
    """
    Compound Annual Growth Rate.
    Uses actual trading days elapsed scaled to a 252-day year.
    """
    n_years = len(df) / TRADING_DAYS_PER_YEAR
    if n_years == 0:
        return 0.0
    return (1 + total_return(df)) ** (1 / n_years) - 1


def annualized_return(dr: pd.Series) -> float:
    """Arithmetic annualized return: mean daily return * 252."""
    return dr.mean() * TRADING_DAYS_PER_YEAR


def annualized_volatility(dr: pd.Series) -> float:
    """Annualized standard deviation of daily returns."""
    return dr.std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def summary(price_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Compute return metrics for every ticker in price_data.

    Returns a DataFrame with tickers as rows and metrics as columns:
        total_return, cagr, annualized_return, annualized_volatility
    """
    rows = []
    for ticker, df in price_data.items():
        if len(df) < 2:
            continue
        dr = daily_returns(df)
        rows.append({
            "ticker":               ticker,
            "total_return":         total_return(df),
            "cagr":                 cagr(df),
            "annualized_return":    annualized_return(dr),
            "annualized_volatility": annualized_volatility(dr),
        })

    result = pd.DataFrame(rows).set_index("ticker")

    pct_cols = ["total_return", "cagr", "annualized_return", "annualized_volatility"]
    for col in pct_cols:
        result[col] = pd.to_numeric(result[col])

    return result
