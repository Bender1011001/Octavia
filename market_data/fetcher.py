import yfinance as yf
import pandas as pd
from fredapi import Fred
from typing import Optional, Dict, Tuple, List, Union
import os

class DataFetcher:
    """
    Handles fetching data from external APIs like yfinance and FRED.
    Includes in-memory caching and methods to store data to CSV.
    """
    def __init__(self, fred_api_key: Optional[str] = None):
        self.fred = Fred(api_key=fred_api_key) if fred_api_key else None
        self.stock_cache: Dict[Tuple[str, str, str], pd.DataFrame] = {}
        self.econ_cache: Dict[Tuple[str, str, str], pd.Series] = {}

    def get_stock_data(self, ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Get historical stock data from yfinance, with in-memory caching.
        """
        cache_key = (ticker, start_date, end_date)
        if cache_key in self.stock_cache:
            return self.stock_cache[cache_key]
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(start=start_date, end=end_date)
            self.stock_cache[cache_key] = data
            return data
        except Exception as e:
            print(f"Error fetching stock data for {ticker}: {e}")
            return None

    def get_economic_data(self, series_id: str, start_date: str, end_date: str) -> Optional[pd.Series]:
        """
        Get economic data from FRED, with in-memory caching.
        """
        if not self.fred:
            print("FRED API key not provided. Cannot fetch economic data.")
            return None
        cache_key = (series_id, start_date, end_date)
        if cache_key in self.econ_cache:
            return self.econ_cache[cache_key]
        try:
            data = self.fred.get_series(series_id, start_date, end_date)
            self.econ_cache[cache_key] = data
            return data
        except Exception as e:
            print(f"Error fetching FRED data for {series_id}: {e}")
            return None

    def save_stock_data_to_csv(self, data: pd.DataFrame, ticker: str, out_dir: str = "market_data/data"):
        """
        Save stock data DataFrame to CSV.
        """
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{ticker}_stock_data.csv")
        data.to_csv(out_path)
        print(f"Saved stock data for {ticker} to {out_path}")

    def save_economic_data_to_csv(self, data: pd.Series, series_id: str, out_dir: str = "market_data/data"):
        """
        Save economic data Series to CSV.
        """
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{series_id}_fred_data.csv")
        data.to_csv(out_path, header=True)
        print(f"Saved FRED data for {series_id} to {out_path}")

def fetch_and_store_all(
    tickers: List[str],
    fred_series: List[str],
    start_date: str,
    end_date: str,
    fred_api_key: Optional[str] = None,
    out_dir: str = "market_data/data"
):
    """
    Fetch and store historical stock and economic data for given tickers and FRED series.
    """
    fetcher = DataFetcher(fred_api_key=fred_api_key)
    for ticker in tickers:
        stock_data = fetcher.get_stock_data(ticker, start_date, end_date)
        if stock_data is not None:
            fetcher.save_stock_data_to_csv(stock_data, ticker, out_dir=out_dir)
    for series_id in fred_series:
        econ_data = fetcher.get_economic_data(series_id, start_date, end_date)
        if econ_data is not None:
            fetcher.save_economic_data_to_csv(econ_data, series_id, out_dir=out_dir)

if __name__ == "__main__":
    # Example usage: edit these lists and dates as needed
    tickers = ["AAPL", "MSFT"]
    fred_series = ["FEDFUNDS", "CPIAUCSL"]
    start_date = "2015-01-01"
    end_date = "2024-01-01"
    fred_api_key = os.environ.get("FRED_API_KEY")  # Set your FRED API key as an environment variable
    fetch_and_store_all(tickers, fred_series, start_date, end_date, fred_api_key=fred_api_key)