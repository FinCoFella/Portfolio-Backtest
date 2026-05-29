import time
import requests
import pandas as pd


BASE_URL = "https://financialmodelingprep.com/stable"
_REQUEST_DELAY = 0.25  # seconds between ticker fetches to avoid rate limiting


class FMPError(Exception):
    pass


class FMPClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise FMPError("API key is required.")
        self.api_key = api_key
        self._session = requests.Session()

    def get_historical_prices(
        self, ticker: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Fetch daily closing prices for a single ticker or index.

        Stocks/ETFs: uses the dividend-adjusted endpoint (adjClose).
        Indices (symbol starts with ^): uses the full EOD endpoint (close).

        Returns a DataFrame indexed by date (ascending) with columns:
            adj_close, volume
        """
        is_index = ticker.startswith("^")

        if is_index:
            url = f"{BASE_URL}/historical-price-eod/full"
            close_field = "close"
        else:
            url = f"{BASE_URL}/historical-price-eod/dividend-adjusted"
            close_field = "adjClose"

        params = {
            "symbol": ticker,
            "from":   start_date,
            "to":     end_date,
            "apikey": self.api_key,
        }

        try:
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise FMPError(f"HTTP error fetching {ticker}: {e}") from e
        except requests.exceptions.RequestException as e:
            raise FMPError(f"Network error fetching {ticker}: {e}") from e

        data = resp.json()

        if isinstance(data, dict) and "Error Message" in data:
            raise FMPError(f"FMP API error for {ticker}: {data['Error Message']}")

        if not data:
            raise FMPError(
                f"No data returned for '{ticker}' between {start_date} and {end_date}. "
                "Check that the ticker is valid and the date range contains trading days."
            )

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        df = df.rename(columns={close_field: "adj_close"})
        df = df[["adj_close", "volume"]].copy()
        df["adj_close"] = pd.to_numeric(df["adj_close"], errors="coerce")
        df["volume"]    = pd.to_numeric(df["volume"],    errors="coerce").astype("Int64")

        return df

    def get_multiple_tickers(
        self, tickers: list[str], start_date: str, end_date: str
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch historical prices for a list of tickers.
        Returns a dict mapping ticker symbol -> DataFrame.
        Skips tickers that fail with a printed warning.
        """
        results: dict[str, pd.DataFrame] = {}
        for i, ticker in enumerate(tickers):
            if i > 0:
                time.sleep(_REQUEST_DELAY)
            try:
                df = self.get_historical_prices(ticker, start_date, end_date)
                results[ticker] = df
                print(f"  [{ticker}] fetched {len(df)} trading days")
            except FMPError as e:
                print(f"  [{ticker}] WARNING: {e}")
        return results
