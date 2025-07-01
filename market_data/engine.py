from .fetcher import DataFetcher
from .modeler import FinancialModeler
import pandas as pd
from typing import Dict, Optional

class MarketDataEngine:
    """
    Orchestrates fetching, processing, and providing real-world market data.
    """
    def __init__(self, tickers: list, fred_series: dict, fred_api_key: Optional[str] = None):
        self.tickers = tickers
        self.fred_series = fred_series
        self.fetcher = DataFetcher(fred_api_key=fred_api_key)
        self.modeler = FinancialModeler()
        self.data = self._load_initial_data()

    def _load_initial_data(self) -> Dict[str, pd.DataFrame]:
        """
        Load initial historical data for all assets.
        """
        data = {}
        for ticker in self.tickers:
            # Fetch last 5 years of data
            df = self.fetcher.get_stock_data(ticker, start_date="2020-01-01", end_date="2024-12-31")
            if df is not None:
                data[ticker] = df
        
        for name, series_id in self.fred_series.items():
            series = self.fetcher.get_economic_data(series_id, start_date="2020-01-01", end_date="2024-12-31")
            if series is not None:
                data[name] = series.to_frame(name=name)
        return data

    def get_market_update(self, current_date: pd.Timestamp) -> Dict:
        """
        Fetch and process market data for the current simulation tick.
        For each tick, fetch new prices and economic data, and process with FinancialModeler.
        Output is structured for easy consumption by the simulation engine.
        """
        update = {"prices": {}, "economic": {}, "modeling": {}}

        # Parameters
        window_days = 30  # Window size for modeling (e.g., GARCH)
        start_window = (current_date - pd.Timedelta(days=window_days)).strftime("%Y-%m-%d")
        end_window = current_date.strftime("%Y-%m-%d")

        # Fetch latest prices and window for modeling
        price_series = {}
        for ticker in self.tickers:
            # Fetch window of prices for modeling
            df = self.fetcher.get_stock_data(ticker, start_date=start_window, end_date=end_window)
            if df is not None and not df.empty:
                # Latest price for this tick
                latest_price = df['Close'].asof(current_date)
                update["prices"][ticker] = latest_price
                # Store for modeling
                price_series[ticker] = df['Close']

        # Fetch latest economic data
        for name, series_id in self.fred_series.items():
            series = self.fetcher.get_economic_data(series_id, start_date=start_window, end_date=end_window)
            if series is not None and not series.empty:
                latest_value = series.asof(current_date)
                update["economic"][name] = latest_value

        # Financial modeling: GARCH volatility and correlation matrix
        # Compute returns DataFrame
        returns_df = pd.DataFrame({ticker: s.pct_change().dropna() for ticker, s in price_series.items() if len(s) > 1})
        modeling = {}

        # GARCH volatility forecast for each ticker
        for ticker, returns in returns_df.items():
            vol = self.modeler.calculate_garch_forecast(returns)
            modeling[f"{ticker}_volatility"] = vol

        # Correlation matrix
        if not returns_df.empty and returns_df.shape[1] > 1:
            corr = self.modeler.calculate_correlation_matrix(returns_df)
            if corr is not None:
                modeling["correlation_matrix"] = corr.to_dict()

        update["modeling"] = modeling

        return update