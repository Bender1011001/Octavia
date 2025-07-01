import unittest
import numpy as np
import pandas as pd
from market_data.modeler import FinancialModeler

class TestFinancialModeler(unittest.TestCase):
    def setUp(self):
        self.modeler = FinancialModeler()

    def test_garch_forecast_valid(self):
        # Simulate returns with some volatility
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0, 0.01, 100))
        forecast = self.modeler.calculate_garch_forecast(returns)
        self.assertIsInstance(forecast, float)
        self.assertGreater(forecast, 0)

    def test_garch_forecast_empty(self):
        returns = pd.Series(dtype=float)
        forecast = self.modeler.calculate_garch_forecast(returns)
        self.assertIsNone(forecast)

    def test_correlation_matrix_valid(self):
        # Simulate returns for 3 stocks
        np.random.seed(42)
        data = np.random.normal(0, 0.01, (100, 3))
        returns_df = pd.DataFrame(data, columns=['A', 'B', 'C'])
        corr_matrix = self.modeler.calculate_correlation_matrix(returns_df)
        self.assertIsInstance(corr_matrix, pd.DataFrame)
        self.assertEqual(corr_matrix.shape, (3, 3))
        # Diagonal should be 1
        np.testing.assert_array_almost_equal(np.diag(corr_matrix), np.ones(3))

    def test_correlation_matrix_empty(self):
        returns_df = pd.DataFrame()
        corr_matrix = self.modeler.calculate_correlation_matrix(returns_df)
        self.assertIsNone(corr_matrix)

if __name__ == "__main__":
    unittest.main()