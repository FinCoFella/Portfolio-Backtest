import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "Miscellaneous" / ".env")

from src.data.fmp_client     import FMPClient, FMPError
from src.metrics             import returns  as ret_metrics
from src.metrics             import risk     as risk_metrics
from src.metrics             import ratios   as ratio_metrics
from src.metrics             import relative as rel_metrics
from src.portfolio           import portfolio
from src.export              import excel    as excel_export
from src.export              import pdf      as pdf_export
from src.cli.inputs          import (
    parse_tickers, parse_date, parse_end_date,
    parse_risk_free_rate, parse_benchmark, parse_weights,
)
from src.cli.display         import print_table, preview_data, display_name


def main() -> None:
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        print("ERROR: FMP_API_KEY not found in Miscellaneous/.env")
        sys.exit(1)

    print("\n=== Portfolio Backtest ===\n")

    # ── User inputs ───────────────────────────────────────────────────────────
    tickers        = parse_tickers("Tickers (comma-separated): ")
    start          = parse_date("Start date (YYYY-MM-DD): ")
    end            = parse_end_date()
    risk_free_rate = parse_risk_free_rate()
    benchmark      = parse_benchmark()

    # ── Fetch data ────────────────────────────────────────────────────────────
    all_tickers = tickers if benchmark in tickers else tickers + [benchmark]
    print(f"\nFetching data for {', '.join(all_tickers)} from {start} to {end}...\n")

    client = FMPClient(api_key)
    try:
        data = client.get_multiple_tickers(all_tickers, start, end)
    except FMPError as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

    if not data:
        print("No data retrieved. Check your tickers and date range.")
        sys.exit(1)

    portfolio_tickers = [t for t in tickers if t in data]
    ticker_data       = {t: data[t] for t in portfolio_tickers}

    # ── Pricing preview ───────────────────────────────────────────────────────
    preview_data(data)

    # ── Per-ticker metrics ────────────────────────────────────────────────────
    # comparison_data adds the benchmark so it appears alongside portfolio tickers
    # in return, risk, and ratio tables. Relative metrics use ticker_data only
    # since the benchmark cannot be compared against itself.
    comparison_data = dict(ticker_data)
    if benchmark in data:
        comparison_data[display_name(benchmark)] = data[benchmark]

    pct_ret  = {"total_return", "cagr", "annualized_return", "annualized_volatility"}
    risk_sum = risk_metrics.summary(comparison_data, confidence=0.95)
    pct_risk = set(risk_sum.columns)

    print("\n================================== Return Metrics ==================================\n")
    print_table(ret_metrics.summary(comparison_data), pct_cols=pct_ret)

    print("\n========================= Risk Metrics (95% confidence) ==========================\n")
    print_table(risk_sum, pct_cols=pct_risk)

    print("\n====== Risk-Adjusted Ratios ======\n")
    print_table(ratio_metrics.summary(comparison_data, risk_free_rate=risk_free_rate))

    if benchmark in data:
        pct_rel = {"alpha", "excess_return", "tracking_error"}
        print(f"\n==================================== Relative Metrics vs {display_name(benchmark)} ====================================\n")
        print_table(
            rel_metrics.summary(ticker_data, data[benchmark], benchmark, risk_free_rate),
            pct_cols=pct_rel,
        )

    # ── Portfolio ─────────────────────────────────────────────────────────────
    weights       = parse_weights(portfolio_tickers)
    port_returns  = portfolio.build(data, weights)
    bench_returns = ret_metrics.daily_returns(data[benchmark]) if benchmark in data else None

    portfolio.summary(
        port_returns,
        weights,
        risk_free_rate=risk_free_rate,
        benchmark_returns=bench_returns,
        benchmark_ticker=display_name(benchmark) if benchmark in data else None,
    )

    # ── Excel & PDF exports (weights now known) ───────────────────────────────
    export_dir = Path(__file__).parent / "Client" / "Pricing Data"
    saved_path = excel_export.export_pricing(
        data, export_dir, start, end,
        benchmark_ticker=benchmark,
        risk_free_rate=risk_free_rate,
        weights=weights,
    )
    print(f"\nPricing data saved to: {saved_path.name}")

    tearsheet_dir = Path(__file__).parent / "Client" / "Tearsheet"
    pdf_path = pdf_export.export_tearsheet(
        price_data=data,
        ticker_data=ticker_data,
        portfolio_returns=port_returns,
        weights=weights,
        benchmark_ticker=benchmark if benchmark in data else None,
        risk_free_rate=risk_free_rate,
        start_date=start,
        end_date=end,
        output_dir=tearsheet_dir,
    )
    print(f"Tearsheet saved to:  {pdf_path.name}\n")


if __name__ == "__main__":
    main()
