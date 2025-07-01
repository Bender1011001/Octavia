import unittest
import tempfile
import json
import os
from decimal import Decimal
from pathlib import Path
from config_loader import ConfigLoader
from backends import TradeBackend, ProjectBackend, DebtBackend


class TestConfigSystem(unittest.TestCase):
    """Test the configuration system for financial data."""
    
    def setUp(self):
        """Set up test environment with temporary config directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_loader = ConfigLoader(self.temp_dir)
        
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_stocks_config_loading(self):
        """Test loading stocks from configuration file."""
        # Create test stocks config
        stocks_config = {
            "stocks": {
                "TEST": {"ticker": "TEST", "price": "100.00"},
                "DEMO": {"ticker": "DEMO", "price": "200.00"}
            }
        }
        
        config_file = Path(self.temp_dir) / "stocks.json"
        with open(config_file, 'w') as f:
            json.dump(stocks_config, f)
            
        # Test loading
        loaded_stocks = self.config_loader.load_stocks_config()
        self.assertEqual(len(loaded_stocks), 2)
        self.assertEqual(loaded_stocks["TEST"]["price"], "100.00")
        self.assertEqual(loaded_stocks["DEMO"]["price"], "200.00")
        
    def test_stocks_fallback_to_defaults(self):
        """Test fallback to default stocks when config file is missing."""
        # No config file created - should use defaults
        loaded_stocks = self.config_loader.load_stocks_config()
        
        # Should contain default stocks
        self.assertIn("AAPL", loaded_stocks)
        self.assertIn("GOOGL", loaded_stocks)
        self.assertEqual(loaded_stocks["AAPL"]["price"], "150.00")
        
    def test_projects_config_loading(self):
        """Test loading projects from configuration file."""
        # Create test projects config
        projects_config = {
            "projects": [
                {
                    "project_id": "TEST-001",
                    "name": "Test Project",
                    "required_investment": "10000.00",
                    "expected_return_pct": "0.15",
                    "risk_level": "MEDIUM",
                    "weeks_to_completion": 5,
                    "success_probability": "0.8"
                }
            ]
        }
        
        config_file = Path(self.temp_dir) / "projects.json"
        with open(config_file, 'w') as f:
            json.dump(projects_config, f)
            
        # Test loading
        loaded_projects = self.config_loader.load_projects_config()
        self.assertEqual(len(loaded_projects), 1)
        self.assertEqual(loaded_projects[0]["project_id"], "TEST-001")
        self.assertEqual(loaded_projects[0]["required_investment"], "10000.00")
        
    def test_bonds_config_loading(self):
        """Test loading bonds from configuration file."""
        # Create test bonds config
        bonds_config = {
            "bonds": [
                {
                    "bond_id": "TEST-BOND",
                    "name": "Test Bond",
                    "face_value": "1000.00",
                    "coupon_rate": "0.04",
                    "maturity_years": 5,
                    "current_price": "990.00"
                }
            ]
        }
        
        config_file = Path(self.temp_dir) / "bonds.json"
        with open(config_file, 'w') as f:
            json.dump(bonds_config, f)
            
        # Test loading
        loaded_bonds = self.config_loader.load_bonds_config()
        self.assertEqual(len(loaded_bonds), 1)
        self.assertEqual(loaded_bonds[0]["bond_id"], "TEST-BOND")
        self.assertEqual(loaded_bonds[0]["current_price"], "990.00")
        
    def test_market_config_loading(self):
        """Test loading market configuration."""
        # Create test market config
        market_config = {
            "market_parameters": {
                "base_interest_rate": "0.05"
            }
        }
        
        config_file = Path(self.temp_dir) / "market_config.json"
        with open(config_file, 'w') as f:
            json.dump(market_config, f)
            
        # Test loading
        loaded_market = self.config_loader.load_market_config()
        self.assertEqual(loaded_market["base_interest_rate"], "0.05")
        
    def test_trade_backend_with_config(self):
        """Test TradeBackend initialization with custom configuration."""
        # Create custom stocks config
        stocks_config = {
            "stocks": {
                "CUSTOM": {"ticker": "CUSTOM", "price": "500.00"}
            }
        }
        
        config_file = Path(self.temp_dir) / "stocks.json"
        with open(config_file, 'w') as f:
            json.dump(stocks_config, f)
            
        # Initialize backend with custom config
        backend = TradeBackend(self.config_loader)
        
        # Verify custom stock is loaded
        self.assertIn("CUSTOM", backend.stocks)
        self.assertEqual(backend.stocks["CUSTOM"].price, Decimal("500.00"))
        
    def test_project_backend_with_config(self):
        """Test ProjectBackend initialization with custom configuration."""
        # Create custom projects config
        projects_config = {
            "projects": [
                {
                    "project_id": "CUSTOM-001",
                    "name": "Custom Project",
                    "required_investment": "15000.00",
                    "expected_return_pct": "0.20",
                    "risk_level": "HIGH",
                    "weeks_to_completion": 6,
                    "success_probability": "0.7"
                }
            ]
        }
        
        config_file = Path(self.temp_dir) / "projects.json"
        with open(config_file, 'w') as f:
            json.dump(projects_config, f)
            
        # Initialize backend with custom config
        backend = ProjectBackend(self.config_loader)
        
        # Verify custom project is loaded
        self.assertIn("CUSTOM-001", backend.available_projects)
        project = backend.available_projects["CUSTOM-001"]
        self.assertEqual(project.name, "Custom Project")
        self.assertEqual(project.required_investment, Decimal("15000.00"))
        
    def test_debt_backend_with_config(self):
        """Test DebtBackend initialization with custom configuration."""
        # Create custom bonds and market config
        bonds_config = {
            "bonds": [
                {
                    "bond_id": "CUSTOM-BOND",
                    "name": "Custom Bond",
                    "face_value": "1000.00",
                    "coupon_rate": "0.06",
                    "maturity_years": 8,
                    "current_price": "1100.00"
                }
            ]
        }
        
        market_config = {
            "market_parameters": {
                "base_interest_rate": "0.04"
            }
        }
        
        bonds_file = Path(self.temp_dir) / "bonds.json"
        with open(bonds_file, 'w') as f:
            json.dump(bonds_config, f)
            
        market_file = Path(self.temp_dir) / "market_config.json"
        with open(market_file, 'w') as f:
            json.dump(market_config, f)
            
        # Initialize backend with custom config
        backend = DebtBackend(self.config_loader)
        
        # Verify custom bond and interest rate are loaded
        self.assertIn("CUSTOM-BOND", backend.bonds)
        bond = backend.bonds["CUSTOM-BOND"]
        self.assertEqual(bond.name, "Custom Bond")
        self.assertEqual(bond.current_price, Decimal("1100.00"))
        self.assertEqual(backend.base_interest_rate, Decimal("0.04"))
        
    def test_invalid_json_fallback(self):
        """Test fallback behavior when JSON files are invalid."""
        # Create invalid JSON file
        config_file = Path(self.temp_dir) / "stocks.json"
        with open(config_file, 'w') as f:
            f.write("{ invalid json }")
            
        # Should fall back to defaults without crashing
        loaded_stocks = self.config_loader.load_stocks_config()
        self.assertIn("AAPL", loaded_stocks)  # Default stock should be present
        
    def test_backward_compatibility(self):
        """Test that backends work without any configuration files."""
        # Initialize backends without any config files
        trade_backend = TradeBackend(self.config_loader)
        project_backend = ProjectBackend(self.config_loader)
        debt_backend = DebtBackend(self.config_loader)
        
        # Should have default data
        self.assertIn("AAPL", trade_backend.stocks)
        self.assertIn("P-001", project_backend.available_projects)
        self.assertIn("BOND-001", debt_backend.bonds)
        self.assertEqual(debt_backend.base_interest_rate, Decimal("0.03"))


if __name__ == '__main__':
    unittest.main()