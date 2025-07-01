import os
import unittest
from market_data.fetcher import DataFetcher, StockDataFetchError, EconomicDataFetchError

@unittest.skipUnless(os.environ.get("RUN_MARKET_DATA_INTEGRATION_TESTS") == "1",
                     "Set RUN_MARKET_DATA_INTEGRATION_TESTS=1 to enable integration tests")
class TestMarketDataIntegration(unittest.TestCase):
    def setUp(self):
        self.fetcher = DataFetcher()

    def test_get_stock_data_real(self):
        # This test will make a real API call to yfinance
        data = self.fetcher.get_stock_data("AAPL", "2023-01-01", "2023-01-10")
        self.assertIsNotNone(data)
        self.assertFalse(data.empty)
        self.assertIn("Close", data.columns)

    def test_get_economic_data_real(self):
        # This test will make a real API call to FRED
        data = self.fetcher.get_economic_data("FEDFUNDS", "2023-01-01", "2023-01-10")
        self.assertIsNotNone(data)
        self.assertFalse(data.empty)

    def test_stock_data_error(self):
        with self.assertRaises(StockDataFetchError):
            self.fetcher.get_stock_data("INVALID_TICKER", "2023-01-01", "2023-01-10")

    def test_economic_data_error(self):
        with self.assertRaises(EconomicDataFetchError):
            self.fetcher.get_economic_data("INVALID_SERIES", "2023-01-01", "2023-01-10")

if __name__ == "__main__":
    unittest.main()