"""Unit tests for the MarketDataEngine-based market shock and propagation system."""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from market_data.engine import MarketDataEngine

class TestMarketDataEngineShocks:
    """Test cases for MarketDataEngine's ability to generate and propagate market shocks."""

    def setup_method(self):
        # Example tickers and economic series
        self.tickers = ["AAPL", "GOOG"]
        self.fred_series = {"FEDFUNDS": "FEDFUNDS"}
        self.current_date = pd.Timestamp("2024-06-01")
        self.engine = MarketDataEngine(self.tickers, self.fred_series, fred_api_key=None)

    def test_price_shock_propagation(self):
        """Simulate a sudden price drop and verify propagation in market update."""
        # Mock fetcher to simulate a price shock
        shock_price = 50.0
        with patch.object(self.engine.fetcher, "get_stock_data") as mock_get_stock_data:
            # Simulate DataFrame with a sudden drop
            df = pd.DataFrame({"Close": [100.0, shock_price]}, index=[
                pd.Timestamp("2024-05-31"), self.current_date
            ])
            mock_get_stock_data.return_value = df

            update = self.engine.get_market_update(self.current_date)
            assert update["prices"]["AAPL"] == shock_price
            assert update["prices"]["GOOG"] == shock_price

    def test_volatility_shock_propagation(self):
        """Simulate a volatility spike and verify modeling output."""
        with patch.object(self.engine.fetcher, "get_stock_data") as mock_get_stock_data, \
             patch.object(self.engine.modeler, "calculate_garch_forecast") as mock_garch:
            # Simulate price series with high volatility
            df = pd.DataFrame({"Close": [100, 80, 120, 60, 130]}, index=pd.date_range("2024-05-27", periods=5))
            mock_get_stock_data.return_value = df
            mock_garch.return_value = 0.25  # Simulated high volatility

            update = self.engine.get_market_update(self.current_date)
            for ticker in self.tickers:
                assert update["modeling"][f"{ticker}_volatility"] == 0.25

    def test_interest_rate_shock_propagation(self):
        """Simulate a sudden interest rate change and verify economic data propagation."""
        with patch.object(self.engine.fetcher, "get_economic_data") as mock_get_economic_data:
            # Simulate economic series with a rate jump
            series = pd.Series([5.0, 7.5], index=[pd.Timestamp("2024-05-31"), self.current_date])
            mock_get_economic_data.return_value = series

            update = self.engine.get_market_update(self.current_date)
            assert update["economic"]["FEDFUNDS"] == 7.5

    def test_missing_data_handling(self):
        """Test that missing data is handled gracefully."""
        with patch.object(self.engine.fetcher, "get_stock_data", return_value=None), \
             patch.object(self.engine.fetcher, "get_economic_data", return_value=None):
            update = self.engine.get_market_update(self.current_date)
            assert update["prices"] == {}
            assert update["economic"] == {}
            assert update["modeling"] == {}

    def test_partial_data(self):
        """Test that partial data (one ticker missing) is handled correctly."""
        def get_stock_data_side_effect(ticker, *args, **kwargs):
            if ticker == "AAPL":
                return pd.DataFrame({"Close": [100, 110]}, index=[pd.Timestamp("2024-05-31"), self.current_date])
            else:
                return None
        with patch.object(self.engine.fetcher, "get_stock_data", side_effect=get_stock_data_side_effect):
            update = self.engine.get_market_update(self.current_date)
            assert "AAPL" in update["prices"]
            assert "GOOG" not in update["prices"]

    def test_correlation_matrix_output(self):
        """Test that correlation matrix is included when multiple tickers have data."""
        with patch.object(self.engine.fetcher, "get_stock_data") as mock_get_stock_data, \
             patch.object(self.engine.modeler, "calculate_correlation_matrix") as mock_corr:
            # Simulate price series for both tickers
            df = pd.DataFrame({"Close": [100, 110, 120]}, index=pd.date_range("2024-05-29", periods=3))
            mock_get_stock_data.return_value = df
            mock_corr.return_value = pd.DataFrame([[1.0, 0.5], [0.5, 1.0]], columns=self.tickers, index=self.tickers)

            update = self.engine.get_market_update(self.current_date)
            assert "correlation_matrix" in update["modeling"]
            assert update["modeling"]["correlation_matrix"]["AAPL"]["GOOG"] == 0.5