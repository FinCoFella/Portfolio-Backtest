import numpy as np
import pandas as pd

from src.metrics.returns import daily_returns, annualized_return
from src.metrics import risk as risk_metrics
from src.metrics import ratios as ratio_metrics
from src.metrics import relative as rel_metrics

TRADING_DAYS_PER_YEAR = 252


def build(
    price_data: dict[str, pd.DataFrame], weights: dict[str, float]
) -> pd.Series:
    """
    Construct a daily portfolio return series from per-ticker price data and weights.
    weights: dict mapping ticker -> decimal (e.g. {'AAPL': 0.6, 'MSFT': 0.4})
    Dates are aligned on the intersection of all tickers' trading days.
    """
    returns_map = {
        ticker: daily_returns(price_data[ticker])
        for ticker in weights
        if ticker in price_data
    }

    aligned = pd.DataFrame(returns_map).dropna()
    weight_series = pd.Series(weights).reindex(aligned.columns)
    return aligned.mul(weight_series, axis=1).sum(axis=1)


def total_return(portfolio_returns: pd.Series) -> float:
    return float((1 + portfolio_returns).prod() - 1)


def cagr(portfolio_returns: pd.Series) -> float:
    n_years = len(portfolio_returns) / TRADING_DAYS_PER_YEAR
    if n_years == 0:
        return 0.0
    return float((1 + total_return(portfolio_returns)) ** (1 / n_years) - 1)


def summary(
    portfolio_returns: pd.Series,
    weights: dict[str, float],
    risk_free_rate: float = 0.0,
    benchmark_returns: pd.Series = None,
    benchmark_ticker: str = None,
    confidence: float = 0.95,
) -> None:
    """Print a full metrics tearsheet for the portfolio."""
    from tabulate import tabulate

    dr = portfolio_returns

    # ── Return metrics ────────────────────────────────────────────────────────
    ret_rows = [
        ("Total Return",         f"{total_return(dr):.2%}"),
        ("CAGR",                 f"{cagr(dr):.2%}"),
        ("Annualized Return",    f"{annualized_return(dr):.2%}"),
        ("Annualized Volatility",f"{risk_metrics.std_dev_annualized(dr):.2%}"),
    ]

    # ── Risk metrics ──────────────────────────────────────────────────────────
    risk_rows = [
        ("Max Drawdown",                    f"{risk_metrics.max_drawdown(dr):.2%}"),
        (f"VaR {int(confidence*100)}% Daily", f"{risk_metrics.var(dr, confidence):.2%}"),
        (f"ES  {int(confidence*100)}% Daily", f"{risk_metrics.expected_shortfall(dr, confidence):.2%}"),
    ]

    # ── Risk-adjusted ratios ──────────────────────────────────────────────────
    ratio_rows = [
        ("Sharpe Ratio",  f"{ratio_metrics.sharpe(dr, risk_free_rate):.4f}"),
        ("Sortino Ratio", f"{ratio_metrics.sortino(dr, risk_free_rate):.4f}"),
    ]

    # ── Relative metrics ──────────────────────────────────────────────────────
    rel_rows = []
    if benchmark_returns is not None:
        rel_rows = [
            ("Beta",              f"{rel_metrics.beta(dr, benchmark_returns):.4f}"),
            ("Alpha (annualized)",f"{rel_metrics.alpha(dr, benchmark_returns, risk_free_rate):.2%}"),
            ("Treynor Ratio",     f"{rel_metrics.treynor(dr, benchmark_returns, risk_free_rate):.4f}"),
            ("Excess Return",     f"{rel_metrics.excess_return(dr, benchmark_returns):.2%}"),
            ("Tracking Error",    f"{rel_metrics.tracking_error(dr, benchmark_returns):.2%}"),
            ("Information Ratio", f"{rel_metrics.information_ratio(dr, benchmark_returns):.4f}"),
        ]

    # ── Weights ───────────────────────────────────────────────────────────────
    weight_rows = [(ticker, f"{w:.2%}") for ticker, w in weights.items()]

    label = f"vs {benchmark_ticker}" if benchmark_ticker else ""

    print("\n== Portfolio Weights ==\n")
    print(tabulate(weight_rows, headers=["Ticker", "Weight"], tablefmt="rounded_outline"))

    print("\n==== Portfolio Return Metrics ====\n")
    print(tabulate(ret_rows, headers=["Metric", "Value"], tablefmt="rounded_outline"))

    print("\n= Portfolio Risk Metrics (95% confidence) =\n")
    print(tabulate(risk_rows, headers=["Metric", "Value"], tablefmt="rounded_outline"))

    print("\n= Portfolio Risk-Adjusted Ratios =\n")
    print(tabulate(ratio_rows, headers=["Metric", "Value"], tablefmt="rounded_outline"))

    if rel_rows:
        print(f"\n=== Portfolio Relative Metrics {label} ===\n")
        print(tabulate(rel_rows, headers=["Metric", "Value"], tablefmt="rounded_outline"))
