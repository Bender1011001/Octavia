import json
import os
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pathlib import Path

class ConfigLoader:
    """Handles loading configuration files with fallback to default values."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        
    def load_stocks_config(self) -> Dict[str, Dict[str, Any]]:
        """Load stock configuration with fallback to defaults."""
        config_file = self.config_dir / "stocks.json"
        
        # Default stock data (fallback)
        default_stocks = {
            'AAPL': {'ticker': 'AAPL', 'price': '150.00'},
            'GOOGL': {'ticker': 'GOOGL', 'price': '2500.00'},
            'MSFT': {'ticker': 'MSFT', 'price': '300.00'},
            'TSLA': {'ticker': 'TSLA', 'price': '800.00'},
            'AMZN': {'ticker': 'AMZN', 'price': '3200.00'}
        }
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    return data.get('stocks', default_stocks)
            else:
                print(f"Warning: {config_file} not found, using default stock data")
                return default_stocks
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {config_file}: {e}. Using default stock data")
            return default_stocks
            
    def load_projects_config(self) -> List[Dict[str, Any]]:
        """Load project configuration with fallback to defaults."""
        config_file = self.config_dir / "projects.json"
        
        # Default project data (fallback)
        default_projects = [
            {
                "project_id": "P-001",
                "name": "Tech Startup Alpha",
                "required_investment": "50000.00",
                "expected_return_pct": "0.25",
                "risk_level": "HIGH",
                "weeks_to_completion": 8,
                "success_probability": "0.6"
            },
            {
                "project_id": "P-002",
                "name": "Green Energy Initiative",
                "required_investment": "75000.00",
                "expected_return_pct": "0.18",
                "risk_level": "MEDIUM",
                "weeks_to_completion": 12,
                "success_probability": "0.75"
            },
            {
                "project_id": "P-003",
                "name": "Real Estate Development",
                "required_investment": "100000.00",
                "expected_return_pct": "0.15",
                "risk_level": "LOW",
                "weeks_to_completion": 16,
                "success_probability": "0.85"
            },
            {
                "project_id": "P-004",
                "name": "Biotech Research",
                "required_investment": "30000.00",
                "expected_return_pct": "0.35",
                "risk_level": "HIGH",
                "weeks_to_completion": 6,
                "success_probability": "0.5"
            },
            {
                "project_id": "P-005",
                "name": "Infrastructure Bond",
                "required_investment": "25000.00",
                "expected_return_pct": "0.08",
                "risk_level": "LOW",
                "weeks_to_completion": 4,
                "success_probability": "0.95"
            }
        ]
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    return data.get('projects', default_projects)
            else:
                print(f"Warning: {config_file} not found, using default project data")
                return default_projects
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {config_file}: {e}. Using default project data")
            return default_projects
            
    def load_bonds_config(self) -> List[Dict[str, Any]]:
        """Load bond configuration with fallback to defaults."""
        config_file = self.config_dir / "bonds.json"
        
        # Default bond data (fallback)
        default_bonds = [
            {
                "bond_id": "BOND-001",
                "name": "US Treasury 10Y",
                "face_value": "1000.00",
                "coupon_rate": "0.025",
                "maturity_years": 10,
                "current_price": "980.00"
            },
            {
                "bond_id": "BOND-002",
                "name": "Corporate AAA 5Y",
                "face_value": "1000.00",
                "coupon_rate": "0.035",
                "maturity_years": 5,
                "current_price": "1020.00"
            },
            {
                "bond_id": "BOND-003",
                "name": "Municipal 7Y",
                "face_value": "1000.00",
                "coupon_rate": "0.028",
                "maturity_years": 7,
                "current_price": "995.00"
            },
            {
                "bond_id": "BOND-004",
                "name": "High Yield 3Y",
                "face_value": "1000.00",
                "coupon_rate": "0.065",
                "maturity_years": 3,
                "current_price": "950.00"
            },
            {
                "bond_id": "BOND-005",
                "name": "Treasury TIPS 15Y",
                "face_value": "1000.00",
                "coupon_rate": "0.015",
                "maturity_years": 15,
                "current_price": "1050.00"
            }
        ]
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    return data.get('bonds', default_bonds)
            else:
                print(f"Warning: {config_file} not found, using default bond data")
                return default_bonds
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {config_file}: {e}. Using default bond data")
            return default_bonds
            
    def load_market_config(self) -> Dict[str, Any]:
        """Load market configuration with fallback to defaults."""
        config_file = self.config_dir / "market_config.json"
        
        # Default market parameters (fallback)
        default_market = {
            "base_interest_rate": "0.03"
        }
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    return data.get('market_parameters', default_market)
            else:
                print(f"Warning: {config_file} not found, using default market parameters")
                return default_market
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {config_file}: {e}. Using default market parameters")
            return default_market