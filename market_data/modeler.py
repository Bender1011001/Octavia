import pandas as pd
import numpy as np
from arch import arch_model
from typing import Optional

class FinancialModeler:
    """
    Handles financial modeling, including GARCH for volatility and correlation matrices.
    """
    def calculate_garch_forecast(self, returns: pd.Series) -> Optional[float]:
        """
        Calculate GARCH(1,1) volatility forecast.
        """
        if returns.empty:
            return None
        try:
            model = arch_model(returns, vol='Garch', p=1, q=1)
            results = model.fit(disp='off')
            forecast = results.forecast(horizon=1)
            return np.sqrt(forecast.variance.iloc[-1, 0])
        except Exception as e:
            print(f"Error calculating GARCH forecast: {e}")
            return None

    def calculate_correlation_matrix(self, returns_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Calculate the correlation matrix for a DataFrame of returns.
        """
        if returns_df.empty:
            return None
        try:
            return returns_df.corr()
        except Exception as e:
            print(f"Error calculating correlation matrix: {e}")
            return None