from decimal import Decimal
import pytest
from ledger import Ledger
from models import AssetHolding
from backends import TradeBackend

@pytest.fixture
def price_provider():
    return TradeBackend()

def test_ledger_initialization(price_provider):
    """Test ledger starts with correct cash and empty assets."""
    initial_cash = Decimal('1000.00')
    ledger = Ledger(initial_cash, price_provider)
    assert ledger.cash == initial_cash
    assert ledger.assets == []
    assert ledger.price_provider is not None

def test_add_asset_success(price_provider):
    """Test successfully adding an asset."""
    ledger = Ledger(Decimal('1000.00'), price_provider)
    added = ledger.add_asset('EQUITY', 'AAPL', Decimal('10'), Decimal('500.00'))
    assert added is True
    assert ledger.cash == Decimal('500.00')
    assert len(ledger.assets) == 1
    assert ledger.assets[0].identifier == 'AAPL'

def test_add_asset_insufficient_funds(price_provider):
    """Test adding asset fails when insufficient cash."""
    ledger = Ledger(Decimal('100.00'), price_provider)
    added = ledger.add_asset('EQUITY', 'AAPL', Decimal('10'), Decimal('500.00'))
    assert added is False
    assert ledger.cash == Decimal('100.00')
    assert len(ledger.assets) == 0

def test_remove_asset_success_with_market_price(price_provider):
    """Test successfully removing an asset with market price."""
    ledger = Ledger(Decimal('2000.00'), price_provider) # Initial cash
    added = ledger.add_asset('EQUITY', 'AAPL', Decimal('10'), Decimal('1500.00')) # 10 shares costing $1500 total
    assert added is True
    
    # After purchase: cash = 2000 - 1500 = 500
    assert ledger.cash == Decimal('500.00')
    
    price_provider.update_prices({'AAPL': Decimal('160')}) # Price goes up to $160 per share
    
    removed, proceeds = ledger.remove_asset('EQUITY', 'AAPL', Decimal('5'))
    assert removed is True
    assert proceeds == Decimal('800.00') # 5 shares * $160 market price
    
    # Expected cash calculation:
    # Starting cash after purchase: 500
    # Proceeds from sale: 800
    # Final cash: 500 + 800 = 1300
    assert ledger.cash == Decimal('1300.00')
    assert ledger.assets[0].quantity == Decimal('5')
    
    # Verify cost basis is also updated proportionally
    # Original cost basis: 1500 for 10 shares = 150 per share
    # After selling 5 shares: remaining cost basis should be 5 * 150 = 750
    assert ledger.assets[0].cost_basis == Decimal('750.00')

def test_remove_asset_insufficient_quantity(price_provider):
    """Test removing more than owned fails."""
    ledger = Ledger(Decimal('1000.00'), price_provider)
    ledger.add_asset('EQUITY', 'AAPL', Decimal('10'), Decimal('500.00'))
    removed, proceeds = ledger.remove_asset('EQUITY', 'AAPL', Decimal('15'))
    assert removed is False
    assert proceeds == Decimal('0.00')
    assert ledger.cash == Decimal('500.00')
    assert ledger.assets[0].quantity == Decimal('10')

def test_nav_calculation_with_market_prices(price_provider):
    """Test NAV calculation with cash and market prices."""
    ledger = Ledger(Decimal('2000.00'), price_provider) # Increased initial cash
    ledger.add_asset('EQUITY', 'AAPL', Decimal('10'), Decimal('1500.00')) # Cost basis 150
    price_provider.update_prices({'AAPL': Decimal('160')})
    
    # NAV = cash + market_value = (2000-1500) + (10 * 160) = 500 + 1600 = 2100
    assert ledger.get_nav() == Decimal('2100.00')

def test_portfolio_holdings_with_market_value(price_provider):
    """Test getting portfolio holdings with market value."""
    ledger = Ledger(Decimal('2000.00'), price_provider) # Increased initial cash
    ledger.add_asset('EQUITY', 'AAPL', Decimal('10'), Decimal('1500.00'))
    price_provider.update_prices({'AAPL': Decimal('160')})
    
    holdings = ledger.get_portfolio_holdings()
    assert len(holdings) == 1
    assert holdings[0].current_value == Decimal('1600.00') # 10 * 160

def test_multiple_same_assets(price_provider):
    """Test adding multiple quantities of same asset."""
    ledger = Ledger(Decimal('2000.00'), price_provider)
    ledger.add_asset('EQUITY', 'AAPL', Decimal('10'), Decimal('500.00'))
    ledger.add_asset('EQUITY', 'AAPL', Decimal('5'), Decimal('250.00'))
    assert ledger.cash == Decimal('1250.00')
    assert len(ledger.assets) == 1
    assert ledger.assets[0].quantity == Decimal('15')
    assert ledger.assets[0].cost_basis == Decimal('750.00')

def test_nav_calculation_with_mixed_assets():
    """Test NAV calculation with stocks, bonds, and projects."""
    from backends import TradeBackend
    
    # Create a mock backend that supports bonds
    class MockBackend(TradeBackend):
        def get_bond_price(self, bond_id):
            bond_prices = {'BOND001': Decimal('105.00'), 'BOND002': Decimal('98.50')}
            return bond_prices.get(bond_id)
    
    backend = MockBackend()
    ledger = Ledger(Decimal('10000.00'), backend)
    
    # Add mixed assets
    ledger.add_asset('EQUITY', 'AAPL', Decimal('10'), Decimal('1500.00'))  # $150 per share
    ledger.add_asset('BOND', 'BOND001', Decimal('20'), Decimal('2000.00'))  # $100 per bond initially
    ledger.add_asset('PROJECT', 'PROJ001', Decimal('1'), Decimal('3000.00'))  # $3000 project
    
    # Update market prices
    backend.update_prices({'AAPL': Decimal('160.00')})  # Stock price up
    # Bond price is 105.00 (up from 100.00 cost basis)
    
    # Calculate expected NAV:
    # Cash: 10000 - 1500 - 2000 - 3000 = 3500
    # AAPL: 10 shares * $160 = 1600
    # BOND001: 20 bonds * $105 = 2100
    # PROJECT: cost basis = 3000 (no market price available)
    # Total NAV = 3500 + 1600 + 2100 + 3000 = 10200
    
    nav = ledger.get_nav()
    assert nav == Decimal('10200.00')

def test_portfolio_holdings_with_mixed_assets():
    """Test portfolio holdings with different asset types."""
    from backends import TradeBackend
    
    class MockBackend(TradeBackend):
        def get_bond_price(self, bond_id):
            return Decimal('102.00') if bond_id == 'BOND001' else None
    
    backend = MockBackend()
    ledger = Ledger(Decimal('5000.00'), backend)
    
    # Add different asset types
    ledger.add_asset('EQUITY', 'AAPL', Decimal('5'), Decimal('750.00'))
    ledger.add_asset('BOND', 'BOND001', Decimal('10'), Decimal('1000.00'))
    ledger.add_asset('PROJECT', 'PROJ001', Decimal('1'), Decimal('2000.00'))
    
    # Update stock price
    backend.update_prices({'AAPL': Decimal('160.00')})
    
    holdings = ledger.get_portfolio_holdings()
    
    # Should have 3 holdings
    assert len(holdings) == 3
    
    # Find each holding
    equity_holding = next(h for h in holdings if h.asset_type == 'EQUITY')
    bond_holding = next(h for h in holdings if h.asset_type == 'BOND')
    project_holding = next(h for h in holdings if h.asset_type == 'PROJECT')
    
    # Verify values
    assert equity_holding.current_value == Decimal('800.00')  # 5 * 160
    assert bond_holding.current_value == Decimal('1020.00')  # 10 * 102
    assert project_holding.current_value == Decimal('2000.00')  # cost basis