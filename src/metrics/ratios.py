import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def sharpe(dr: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Sharpe ratio: annualized excess return per unit of annualized volatility.
    risk_free_rate should be an annualized decimal (e.g. 0.05 for 5%).
    """
    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess = dr - daily_rf
    if excess.std() == 0:
        return np.nan
    return float((excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS_PER_YEAR))


def sortino(dr: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Sortino ratio: annualized excess return per unit of downside deviation.
    Downside deviation only penalizes returns that fall below the risk-free rate,
    making it a more targeted measure of harmful volatility than Sharpe.
    risk_free_rate should be an annualized decimal (e.g. 0.05 for 5%).
    """
    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess = dr - daily_rf
    downside_dev = np.sqrt(np.mean(np.minimum(excess, 0) ** 2)) * np.sqrt(TRADING_DAYS_PER_YEAR)
    if downside_dev == 0:
        return np.nan
    annualized_excess = excess.mean() * TRADING_DAYS_PER_YEAR
    return float(annualized_excess / downside_dev)


def summary(
    price_data: dict[str, pd.DataFrame], risk_free_rate: float = 0.0
) -> pd.DataFrame:
    """
    Compute Sharpe and Sortino ratios for every ticker in price_data.
    risk_free_rate should be an annualized decimal (e.g. 0.05 for 5%).
    """
    from src.metrics.returns import daily_returns

    rows = []
    for ticker, df in price_data.items():
        if len(df) < 2:
            continue
        dr = daily_returns(df)
        rows.append({
            "ticker":  ticker,
            "sharpe":  sharpe(dr, risk_free_rate),
            "sortino": sortino(dr, risk_free_rate),
        })

    return pd.DataFrame(rows).set_index("ticker")
