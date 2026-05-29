from datetime import datetime, date


def parse_tickers(prompt: str) -> list[str]:
    while True:
        raw = input(prompt).strip()
        tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
        if tickers:
            return tickers
        print("  Enter at least one ticker.")


def parse_date(prompt: str) -> str:
    while True:
        raw = input(prompt).strip()
        try:
            return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            print("  Invalid format — use YYYY-MM-DD.")


def parse_end_date() -> str:
    if input(f"Today ({date.today()}) as end date? [Y/n]: ").strip().lower() != "n":
        return date.today().strftime("%Y-%m-%d")
    return parse_date("End date (YYYY-MM-DD): ")


def parse_risk_free_rate() -> float:
    raw = input("Annualized risk-free rate (0.00 format): ").strip()
    return float(raw) if raw else 0.0


def parse_benchmark() -> str:
    raw = input("Benchmark ticker [default S&P 500]: ").strip().upper()
    return raw or "^GSPC"


def parse_weights(tickers: list[str]) -> dict[str, float]:
    """
    Prompt for a weight (%) per ticker. Press Enter to accept equal weight.
    Normalizes automatically if weights don't sum to 100.
    """
    n     = len(tickers)
    equal = round(100 / n, 2)
    print(f"\nEnter portfolio weight for each ticker as a percentage.")
    print(f"Press Enter to use equal weight ({equal}% each).\n")

    weights = {}
    for ticker in tickers:
        while True:
            raw = input(f"  {ticker} weight % [default {equal}]: ").strip()
            if not raw:
                weights[ticker] = equal / 100
                break
            try:
                w = float(raw)
                if w < 0:
                    print("  Weight must be non-negative.")
                    continue
                weights[ticker] = w / 100
                break
            except ValueError:
                print("  Enter a number, e.g. 60 for 60%.")

    total = sum(weights.values())
    if abs(total - 1.0) > 0.0005:
        print(f"\n  Weights sum to {total:.2%} — normalizing to 100%.")
        weights = {t: w / total for t, w in weights.items()}

    return weights
