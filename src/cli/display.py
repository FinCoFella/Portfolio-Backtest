import pandas as pd
from tabulate import tabulate


_COLUMN_LABELS: dict[str, str] = {
    "total_return":          "Total Return",
    "cagr":                  "CAGR",
    "annualized_return":     "Annualized Return",
    "annualized_volatility": "Annualized Volatility",
    "std_dev_annualized":    "Std Dev (Ann.)",
    "max_drawdown":          "Max Drawdown",
    "var_95_daily":          "VaR 95% Daily",
    "es_95_daily":           "ES 95% Daily",
    "sharpe":                "Sharpe",
    "sortino":               "Sortino",
    "beta":                  "Beta",
    "alpha":                 "Alpha",
    "treynor":               "Treynor",
    "excess_return":         "Excess Return",
    "tracking_error":        "Tracking Error",
    "information_ratio":     "Information Ratio",
}

_TICKER_DISPLAY: dict[str, str] = {
    "^GSPC": "S&P 500",
    "^DJI":  "Dow Jones",
    "^IXIC": "NASDAQ",
}


def label(col: str) -> str:
    return _COLUMN_LABELS.get(col, col.replace("_", " ").title())


def display_name(ticker: str) -> str:
    return _TICKER_DISPLAY.get(ticker, ticker)


def print_table(df: pd.DataFrame, pct_cols: set = None) -> None:
    display = df.copy().astype(object)
    for col in display.columns:
        if pct_cols and col in pct_cols:
            display[col] = display[col].map(lambda x: f"{x:.2%}")
        else:
            display[col] = display[col].map(
                lambda x: f"{x:.4f}" if isinstance(x, float) else x
            )
    display.columns     = [label(c) for c in display.columns]
    display.index.name  = label(display.index.name) if display.index.name else None
    print(tabulate(display, headers="keys", tablefmt="rounded_outline"))


def preview_data(data: dict, rows: int = 5) -> None:
    closes = pd.DataFrame(
        {display_name(ticker): df["adj_close"] for ticker, df in data.items()}
    )
    sample              = closes.tail(rows).copy()
    sample.index        = sample.index.strftime("%Y-%m-%d")
    sample.index.name   = "Date"
    print("\n============= Adjusted Closing Price =============\n")
    print(tabulate(sample, headers="keys", tablefmt="rounded_outline", floatfmt=".2f"))
