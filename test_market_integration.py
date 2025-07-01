import unittest
import pandas as pd
from decimal import Decimal

from engine import SimulationEngine
from ledger import Ledger
from router import AllocationManager
from backends import TradeBackend, ProjectBackend, DebtBackend
from market_data.engine import MarketDataEngine
from config_loader import ConfigLoader

class TestMarketIntegration(unittest.TestCase):
    def setUp(self):
        """Set up a full simulation environment with the MarketDataEngine."""
        self.config_loader = ConfigLoader(config_path='config')
        
        # Initializing Backends
        self.trade_backend = TradeBackend(self.config_loader)
        self.project_backend = ProjectBackend(self.config_loader)
        self.debt_backend = DebtBackend(self.config_loader)

        # Initializing Ledger and AllocationManager
        self.ledger = Ledger(cash=Decimal('100000'), price_provider=self.trade_backend)
        self.allocation_manager = AllocationManager(
            ledger=self.ledger,
            trade_backend=self.trade_backend,
            project_backend=self.project_backend,
            debt_backend=self.debt_backend
        )

        # Initializing MarketDataEngine
        # NOTE: This requires a FRED API key to be set as an environment variable
        # For this test, we will mock the data fetching
        self.market_data_engine = MarketDataEngine(
            tickers=['AAPL', 'GOOGL'],
            fred_series={'interest_rate': 'DGS10'},
            fred_api_key=None  # Set API key here if running live tests
        )
        
        # Mocking the data fetching to avoid real API calls in tests
        self.market_data_engine.fetcher.get_stock_data = self.mock_get_stock_data
        self.market_data_engine.fetcher.get_economic_data = self.mock_get_economic_data
        self.market_data_engine.data = self.market_data_engine._load_initial_data()

        # Initializing SimulationEngine with the MarketDataEngine
        self.simulation_engine = SimulationEngine(
            ledger=self.ledger,
            allocation_manager=self.allocation_manager,
            market_data_engine=self.market_data_engine
        )

    def mock_get_stock_data(self, ticker, start_date, end_date):
        """Mock yfinance data fetching."""
        dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date))
        prices = [150 + i + (j * 10) for i, date in enumerate(dates)]
        j = 1 if ticker == 'GOOGL' else 0
        return pd.DataFrame({'Close': prices}, index=dates)

    def mock_get_economic_data(self, series_id, start_date, end_date):
        """Mock FRED data fetching."""
        dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date))
        rates = [2.5 + i * 0.01 for i, date in enumerate(dates)]
        return pd.Series(rates, index=dates, name=series_id)

    def test_simulation_tick_updates_prices_and_rates(self):
        """Verify that a simulation tick updates stock prices and interest rates."""
        # Get initial prices and bond yields
        initial_aapl_price = self.trade_backend.get_price('AAPL')
        initial_googl_price = self.trade_backend.get_price('GOOGL')
        initial_bond_price = self.debt_backend.get_bond_price('BOND01')

        # Run one simulation tick
        self.simulation_engine.tick()

        # Get new prices and bond yields
        new_aapl_price = self.trade_backend.get_price('AAPL')
        new_googl_price = self.trade_backend.get_price('GOOGL')
        new_bond_price = self.debt_backend.get_bond_price('BOND01')

        # Assert that prices have changed
        self.assertNotEqual(initial_aapl_price, new_aapl_price)
        self.assertNotEqual(initial_googl_price, new_googl_price)
        self.assertNotEqual(initial_bond_price, new_bond_price)

        # Check the date-specific values from our mock data
        # Day 1: AAPL=151, GOOGL=161, rate=2.51
        # Day 2: AAPL=152, GOOGL=162, rate=2.52
        current_date_tick_1 = self.simulation_engine.start_date + pd.to_timedelta(1, unit='D')
        price_update_1 = self.market_data_engine.get_market_update(current_date_tick_1)
        
        self.assertEqual(self.trade_backend.get_price('AAPL'), Decimal(str(price_update_1['prices']['AAPL'])))
        
        # Run another tick
        self.simulation_engine.tick()
        
        current_date_tick_2 = self.simulation_engine.start_date + pd.to_timedelta(2, unit='D')
        price_update_2 = self.market_data_engine.get_market_update(current_date_tick_2)
        
        self.assertEqual(self.trade_backend.get_price('AAPL'), Decimal(str(price_update_2['prices']['AAPL'])))
        self.assertNotEqual(price_update_1['prices']['AAPL'], price_update_2['prices']['AAPL'])

if __name__ == '__main__':
    unittest.main()