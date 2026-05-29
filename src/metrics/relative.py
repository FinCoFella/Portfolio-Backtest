import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def _align(dr: pd.Series, dr_bench: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Align two return series on their shared dates."""
    combined = pd.concat([dr, dr_bench], axis=1).dropna()
    return combined.iloc[:, 0], combined.iloc[:, 1]


def beta(dr: pd.Series, dr_bench: pd.Series) -> float:
    """
    Sensitivity of the ticker's returns to benchmark returns.
    Beta > 1 means amplified market moves; < 1 means dampened.
    """
    dr, dr_bench = _align(dr, dr_bench)
    cov_matrix = np.cov(dr, dr_bench)
    bench_var = cov_matrix[1, 1]
    if bench_var == 0:
        return np.nan
    return float(cov_matrix[0, 1] / bench_var)


def alpha(
    dr: pd.Series, dr_bench: pd.Series, risk_free_rate: float = 0.0
) -> float:
    """
    Jensen's Alpha (annualized): return earned above what CAPM predicts.
    Positive alpha means the asset outperformed on a risk-adjusted basis.
    risk_free_rate should be an annualized decimal (e.g. 0.05 for 5%).
    """
    dr, dr_bench = _align(dr, dr_bench)
    b = beta(dr, dr_bench)
    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    annualized_return = (dr.mean() - daily_rf) * TRADING_DAYS_PER_YEAR
    annualized_bench  = (dr_bench.mean() - daily_rf) * TRADING_DAYS_PER_YEAR
    return float(annualized_return - b * annualized_bench)


def treynor(
    dr: pd.Series, dr_bench: pd.Series, risk_free_rate: float = 0.0
) -> float:
    """
    Treynor ratio: annualized excess return per unit of beta.
    Similar to Sharpe but uses systematic risk (beta) instead of total risk (vol).
    risk_free_rate should be an annualized decimal (e.g. 0.05 for 5%).
    """
    b = beta(dr, dr_bench)
    if b == 0 or np.isnan(b):
        return np.nan
    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    annualized_excess = (dr.mean() - daily_rf) * TRADING_DAYS_PER_YEAR
    return float(annualized_excess / b)


def excess_return(dr: pd.Series, dr_bench: pd.Series) -> float:
    """
    Annualized return of the ticker minus annualized return of the benchmark.
    """
    dr, dr_bench = _align(dr, dr_bench)
    return float((dr.mean() - dr_bench.mean()) * TRADING_DAYS_PER_YEAR)


def tracking_error(dr: pd.Series, dr_bench: pd.Series) -> float:
    """
    Annualized standard deviation of daily active returns (ticker minus benchmark).
    Measures how consistently the ticker follows — or deviates from — the benchmark.
    """
    dr, dr_bench = _align(dr, dr_bench)
    active = dr - dr_bench
    return float(active.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def information_ratio(dr: pd.Series, dr_bench: pd.Series) -> float:
    """
    Excess return divided by tracking error.
    Measures the consistency with which the ticker generates active return.
    """
    te = tracking_error(dr, dr_bench)
    if te == 0:
        return np.nan
    return float(excess_return(dr, dr_bench) / te)


def summary(
    price_data: dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame,
    benchmark_ticker: str,
    risk_free_rate: float = 0.0,
) -> pd.DataFrame:
    """
    Compute benchmark-relative metrics for every ticker except the benchmark itself.

    Returns a DataFrame with columns:
        beta, alpha, treynor, excess_return, tracking_error, information_ratio
    """
    from src.metrics.returns import daily_returns

    dr_bench = daily_returns(benchmark_df)
    rows = []

    for ticker, df in price_data.items():
        if ticker == benchmark_ticker or len(df) < 2:
            continue
        dr = daily_returns(df)
        rows.append({
            "ticker":           ticker,
            "beta":             beta(dr, dr_bench),
            "alpha":            alpha(dr, dr_bench, risk_free_rate),
            "treynor":          treynor(dr, dr_bench, risk_free_rate),
            "excess_return":    excess_return(dr, dr_bench),
            "tracking_error":   tracking_error(dr, dr_bench),
            "information_ratio": information_ratio(dr, dr_bench),
        })

    return pd.DataFrame(rows).set_index("ticker")
